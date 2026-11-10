"""Small read-only localhost latency/resource experiment; never starts services."""
from concurrent.futures import ThreadPoolExecutor
import math
import os
import statistics
import threading
import time
from urllib.parse import urlsplit
from urllib.request import Request,build_opener,ProxyHandler,HTTPRedirectHandler
from urllib.error import HTTPError,URLError
from .io import ROOT,approved,digest,read,run_directory,write
from .resources import sample


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('Redirects are disabled for local validation.')


def discard_body(response):
    size=0
    while True:
        chunk=response.read(65536)
        if not chunk:break
        size+=len(chunk)
        if size>2*1024**2:raise ValueError('Bounded response budget exceeded.')


def local_url(value):
    parsed=urlsplit(value)
    if (parsed.scheme!='http' or parsed.hostname not in {'127.0.0.1','localhost','::1'} or parsed.username or parsed.password or parsed.query or parsed.fragment
        or parsed.port not in {3000,8000}):raise ValueError('Use a credential-free loopback URL on port3000/8000 without query strings.')
    return value


def request(endpoint,timeout):
    address=local_url(endpoint['url']);headers={}
    token_name=endpoint.get('token_environment')
    if token_name:
        if token_name!='MOVIE_EVALUATION_TOKEN' or not os.environ.get(token_name):return {'endpoint':endpoint['id'],'status':'blocked','seconds':None,'http_status':None}
        headers['Authorization']='Bearer '+os.environ[token_name]
    started=time.perf_counter();code=None;outcome='failed'
    try:
        with build_opener(ProxyHandler({}),NoRedirect()).open(Request(address,headers=headers,method='GET'),timeout=timeout) as response:
            code=response.status
            if code in endpoint.get('expected_statuses',[200]):outcome='passed'
            # Discard bounded chunks so timing includes transfer. Never retain
            # response text,private reviews,query content or tokens in reports.
            discard_body(response)
    except HTTPError as error:
        code=error.code
        try:
            discard_body(error)
            if code in endpoint.get('expected_statuses',[200]):outcome='passed'
        except (OSError,ValueError):outcome='failed'
        finally:error.close()
    except (OSError,URLError,ValueError):outcome='failed'
    return {'endpoint':endpoint['id'],'status':outcome,'seconds':time.perf_counter()-started,'http_status':code}


def percentile(values,fraction):
    if not values:return None
    ordered=sorted(values);position=(len(ordered)-1)*fraction;lower=int(position);upper=math.ceil(position)
    return ordered[lower]+(ordered[upper]-ordered[lower])*(position-lower)


def measure(config_path):
    config_hash=digest(config_path);config=read(config_path);approved(config)
    endpoints=config.get('endpoints',[]);count=config.get('requests_per_endpoint',10);concurrency=config.get('concurrency',1);timeout=config.get('timeout_seconds',5)
    if not endpoints or len(endpoints)>10 or type(count) is not int or not 1<=count<=100 or type(concurrency) is not int or not 1<=concurrency<=4 or not 0<timeout<=15:
        raise ValueError('Use1..10 endpoints,1..100 requests each,1..4 concurrent requests and a timeout at most15seconds.')
    identifiers=[item['id'] for item in endpoints]
    if len(set(identifiers))!=len(identifiers):raise ValueError('Unique endpoint identifiers required.')
    for item in endpoints:local_url(item['url'])
    maximum_duration=config.get('maximum_duration_seconds',120)
    if len(endpoints)*(count+1)>100 or not 5<=maximum_duration<=300:raise ValueError('Keep the trial at most100 requests and5..300seconds.')
    process_ids=config.get('owned_process_ids',[])
    if len(process_ids)>8 or any(type(value) is not int or value<1 for value in process_ids):raise ValueError('Provide at most8 reviewed process IDs.')
    initial=sample(process_ids)
    if initial['available_ram_bytes'] is not None and initial['available_ram_bytes']<config.get('minimum_available_ram_bytes',1024**3):
        raise ValueError('Available RAM is below the approved experiment headroom.')
    resources=[initial];stop=threading.Event()
    def monitor():
        while not stop.is_set():resources.append(sample(process_ids));stop.wait(1)
    monitor_thread=threading.Thread(target=monitor,daemon=True);monitor_thread.start();started=time.perf_counter()
    results=[]
    def bounded_request(endpoint):
        if time.perf_counter()-started>=maximum_duration:return {'endpoint':endpoint['id'],'status':'blocked','seconds':None,'http_status':None}
        return request(endpoint,timeout)
    try:
        for endpoint in endpoints:
            # First observed request is reported separately; it does not prove a cold model cache.
            first=bounded_request(endpoint);first['phase']='first_observed';results.append(first)
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                for value in pool.map(lambda _:bounded_request(endpoint),range(count)):
                    value['phase']='subsequent';results.append(value)
    finally:stop.set();monitor_thread.join(timeout=5)
    elapsed=time.perf_counter()-started;summaries=[]
    for identifier in identifiers:
        group=[row for row in results if row['endpoint']==identifier];successful=[row['seconds'] for row in group if row['status']=='passed' and row['phase']=='subsequent']
        attempted=sum(row['seconds'] is not None for row in group)
        summaries.append({'id':identifier,'scheduled':len(group),'attempted_requests':attempted,'successful':sum(row['status']=='passed' for row in group),
            'p50_seconds_successful_subsequent':percentile(successful,.5),'p95_seconds_successful_subsequent':percentile(successful,.95),
            'error_rate':sum(row['status']=='failed' for row in group)/attempted if attempted else None,'blocked_count':sum(row['status']=='blocked' for row in group)})
    if digest(config_path)!=config_hash:raise ValueError('Benchmark configuration changed during measurement.')
    directory=run_directory('benchmark')
    report={'kind':'bounded_http_benchmark','status':'failed' if any(row['status']=='failed' for row in results) else 'incomplete' if any(row['status']=='blocked' for row in results) else 'passed',
        'config_sha256':config_hash,'elapsed_seconds':elapsed,'observed_requests_per_second':sum(row['seconds'] is not None for row in results)/elapsed,
        'endpoints':summaries,'timings':results,'resources':resources,'gpu_scope':'whole-device sampled memory, not model peak allocation',
        'limitations':'GET endpoints only; no training,model-cache reset,analysis queue latency or inference-quality claim. One-second samples may miss peaks. Failed requests are excluded from successful latency quantiles and reported separately.'}
    report['report_path']=str((directory/'benchmark.json').relative_to(ROOT))
    write(directory/'benchmark.json',report)
    return report
