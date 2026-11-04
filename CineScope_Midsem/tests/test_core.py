import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import analyze,clean,recommend
ROOT=Path(__file__).resolve().parents[1]

class CoreTests(unittest.TestCase):
    def test_opposite_aspects(self):
        r=analyze('The acting was excellent but the story was weak.')
        self.assertEqual(r['aspects']['Acting']['score'],100)
        self.assertEqual(r['aspects']['Story']['score'],0)
        self.assertIsNone(r['aspects']['Music']['score'])
    def test_negation(self):
        self.assertEqual(analyze("The acting wasn't good.")['score'],0)
        self.assertEqual(analyze('The story was not bad.')['score'],100)
    def test_no_evidence(self):
        self.assertIsNone(analyze('The story is about a person.')['aspects']['Story']['score'])
        self.assertIsNone(analyze('')['score'])
    def test_preprocess(self):
        self.assertEqual(clean('<p>gr8 &amp; fun 😊</p>'),'great & fun good')
    def test_theme_and_genre(self):
        r=analyze('The friendship story was excellent. The comedy was awful.')
        self.assertEqual(r['themes']['Friendship']['score'],100)
        self.assertEqual(r['genres']['Comedy']['score'],0)
        self.assertEqual(r['themes']['Friendship']['coverage'],50)
    def test_boundary(self):
        self.assertNotIn('Love',analyze('I loved it.')['themes'])
    def test_excludes_seen_and_prefers_liked_genre(self):
        movies=[dict(id='a',title='Seen',genres=['Comedy']),dict(id='b',title='Comedy',genres=['Comedy']),dict(id='c',title='Horror',genres=['Horror'])]
        r=recommend(movies,[dict(id='a',rating=5,review='')])
        self.assertEqual([m['id'] for m in r],['b','c'])
        d=recommend(movies,[dict(id='a',rating=1,review='')])
        self.assertEqual(d[0]['id'],'c')
    def test_review_signals_reach_ranking(self):
        movies=[dict(id='a',title='Seen',genres=[]),dict(id='b',title='Candidate',genres=[],reviews=['The friendship story was excellent.']),dict(id='c',title='Other',genres=[])]
        r=recommend(movies,[dict(id='a',rating=5,review='The friendship story was excellent.')])
        self.assertEqual(r[0]['id'],'b')
        self.assertGreater(r[0]['components']['theme'],0)
        self.assertGreater(r[0]['components']['aspect'],0)
    def test_ngram_normalizes(self):
        sys.path.insert(0,str(ROOT/'optional'))
        from ngram_lab import NGram
        m=NGram(2).fit(['the story is good','the story is bad'])
        self.assertAlmostEqual(sum(m.probability(['the'],w) for w in m.vocab),1)
        self.assertGreater(m.perplexity(['unseen text']),0)

if __name__=='__main__':unittest.main()
