Checkpoint recovery configuration

The failed run reached 200 optimizer updates but no checkpoint was saved.
The prior guard reused the 3072 MiB startup floor at checkpoint time.
This config retains the 3072 MiB startup floor and sets a separate explicit
2048 MiB available-RAM margin during checkpoint saves, with the existing
20 GiB disk reserve plus estimated checkpoint size. This is a configurable
resource policy, not a guarantee against OOM. All training hyperparameters,
model/source permissions and split manifests are unchanged.
Previous configs/runs are preserved. Start as a fresh run, not Resume.
