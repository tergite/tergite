#!/usr/bin/env python
# coding: utf-8

# # Download logfile from BCC and save to working directory

# In[ ]:


import pathlib

import requests

bcc_url = "http://qtl-axean.mc2.chalmers.se:8000"
job_id = "7c247e9a-658a-418b-b15a-463ad1fa3120"

resp = requests.get(f"{bcc_url}/logfiles/{job_id}")

with open(pathlib.Path(f"{job_id}.hdf5"), mode="wb") as _file:
    _file.write(resp.content)
