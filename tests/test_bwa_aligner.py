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

from tool import bwa_aligner

def test_bwa_aligner():
    resource_path = os.path.join(os.path.dirname(__file__), "data/")
    genome_fa = resource_path + "macs2.Human.GCA_000001405.22.fasta"
    fastqFile = resource_path + "macs2.Human.DRR000150.22.fastq"
    out_bam = fastqFile.replace('.fastq', '.bam')
    
    files = [
        genome_fa,
        genome_fa + ".amb",
        genome_fa + ".ann",
        genome_fa + ".bwt",
        genome_fa + ".pac",
        genome_fa + ".sa"
    ]
    
    
    bwa_amb = files[1]
    bwa_ann = files[2]
    bwa_bwt = files[3]
    bwa_pac = files[4]
    bwa_sa  = files[5]
    
    bwaT = bwa_aligner.bwaAlignerTool()
    bwaT.run([genome_fa, fastqFile, bwa_amb, bwa_ann, bwa_bwt,bwa_pac, bwa_sa], {}, [out_bam]) 
    
    print(__file__)
    
        
def test_bwa_aligner_02():
    resource_path = os.path.join(os.path.dirname(__file__), "data/")
    genome_fa = resource_path + "inps.Mouse.GRCm38.fasta"
    fastqFile = resource_path + "inps.Mouse.GRCm38.fastq"
    out_bam = fastqFile.replace('.fastq', '.bam')
    
    files = [
        genome_fa,
        genome_fa + ".amb",
        genome_fa + ".ann",
        genome_fa + ".bwt",
        genome_fa + ".pac",
        genome_fa + ".sa"
    ]
    
    
    bwa_amb = files[1]
    bwa_ann = files[2]
    bwa_bwt = files[3]
    bwa_pac = files[4]
    bwa_sa  = files[5]
    
    bwaT = bwa_aligner.bwaAlignerTool()
    bwaT.run([genome_fa, fastqFile, bwa_amb, bwa_ann, bwa_bwt,bwa_pac, bwa_sa], {}, [out_bam]) 
    
    print(__file__)