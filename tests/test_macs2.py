#!/usr/bin/python

"""
.. Copyright 2017 EMBL-European Bioinformatics Institute
 
   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at 

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import pytest
import random
import os.path

from tool import macs2

def test_macs2():
    m = macs2.macs2()
    resource_path = os.path.join(os.path.dirname(__file__), "data/")
    
    bam_file = resource_path + "biobambam.Human.DRR000150.22_output.bam"
    if os.path.isfile(bam_file) == False:
        bam_file = resource_path + "macs2.Human.DRR000150.22.bam"
    
    summits_bed = resource_path + "_summits.bed"
    narrowPeak  = resource_path + "_narrowPeak"
    broadPeak   = resource_path + "_broadPeak"
    gappedPeak  = resource_path + "_gappedPeak"

    m.run([bam_file], {}, [summits_bed, narrowPeak, broadPeak, gappedPeak])