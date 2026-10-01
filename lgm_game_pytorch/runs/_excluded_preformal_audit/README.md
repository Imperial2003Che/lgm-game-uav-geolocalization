# Excluded pre-formal audit runs

Nothing in this directory is manuscript evidence.

`university1652_content_seed1_variable_steps` was stopped after epoch 11 of 80
before any official test evaluation. During live log review, the sampler was
found to produce 651–657 optimizer steps across epochs while the learning-rate
scheduler had been initialized from the first-epoch count only. The checkpoint
therefore fails the frozen formal protocol and is retained solely as an
auditable record of why the run was rejected.

The sampler was subsequently changed to assign every real identity chunk to a
fixed number of balanced batches and to assert exact per-epoch coverage before
the formal matrix was restarted from epoch 1.
