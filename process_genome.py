#!/usr/bin/python

"""
.. Copyright 2016 EMBL-European Bioinformatics Institute
 
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

import argparse, urllib2, gzip, shutil, shlex, subprocess, os.path, json

from .. import Tool, Workflow, Metadata
from common import common
from dmp import dmp
import os

try
    from pycompss.api.parameter import FILE_IN, FILE_OUT
    from pycompss.api.task import task
    from pycompss.api.constraint import constraint
except ImportError :
    print "[Warning] Cannot import \"pycompss\" API packages."
    print "          Using mock decorators."
    
    from dummy_pycompss import *

try :
    import pysam
except ImportError :
    print "[Error] Cannot import \"pysam\" package. Have you installed it?"
    exit(-1)

class bowtieIndexerTool(Tool):
    """
    Tool for running indexers over a genome FASTA file
    """
    
    @task()
    def bowtie2_indexer(self, file_loc):
        """
        Bowtie2 Indexer
        """
        cf = common()
        cf.bowtie_index_genome(file_loc)
        return True
    
    def run(self, input_files, metadata):
         """
        Standard function to call a task
        """
        
        # handle error
        if not self.bowtie_indexer(input_files[0]):
            output_metadata.set_exception(
                Exception(
                    "bowtie2_indexer: Could not process files {}, {}.".format(*input_files)))
output_file = None
        return ([output_file], [output_metadata])
    

class bwaIndexerTool(Tool):
    """
    Tool for running indexers over a genome FASTA file
    """
    
    @task()
    def bwa_indexer():
        """
        BWA Indexer
        """
        cf = common()
        cf.bwa_index_genome(file_loc)
        return True
    
    def run(self, input_files, metadata):
         """
        Standard function to call a task
        """
        
        # handle error
        if not self.bwa_indexer(input_files[0]):
            output_metadata.set_exception(
                Exception(
                    "bwa_indexer: Could not process files {}, {}.".format(*input_files)))
output_file = None
        return ([output_file], [output_metadata])
    
    
class gemIndexerTool(Tool):
    """
    Tool for running indexers over a genome FASTA file
    """
    
    @task()
    def gem_indexer():
        """
        GEM Indexer
        """
        cf = common()
        cf.gem_index_genome(file_loc)
        return True
    
    
    def run(self, input_files, metadata):
         """
        Standard function to call a task
        """
        
        # handle error
        if not self.gem_indexer(input_files[0]):
            output_metadata.set_exception(
                Exception(
                    "gem_indexer: Could not process files {}, {}.".format(*input_files)))
output_file = None
        return ([output_file], [output_metadata])


class processs_genome(Workflow):
    """
    Workflow to download and pre-index a given genome
    
    The downloading can be done using the current common.py functions. These
    should be prevented from running the indexing step as this will be done as
    part of this workflow.
    """
    
    def run(self, file_ids, metadata):
        """
        Main run function
        """


if __name__ == "__main__":
    import sys
    import os
    
    from pycompss.api.api import compss_wait_on
    
    # Set up the command line parameters
    parser = argparse.ArgumentParser(description="ChIP-seq peak calling")
    parser.add_argument("--species", help="Species (homo_sapiens)")
    parser.add_argument("--genome", help="Genome FASTA file")
    parser.add_argument("--file", help="Project ID of the dataset")
    parser.add_argument("--bgd_file", help="Project ID of the dataset")
    
    # Get the matching parameters from the command line
    args = parser.parse_args()
    
    species     = args.species
    genome_fa   = args.genome
    file_loc    = args.data_dir
    file_bg_loc = args.tmp_dir
    
    pcs = process_chipseq()
    cf = common()
    
    #
    # MuG Tool Steps
    # --------------
    # 
    # 1. Create data files
    
    # Get the assembly
    genome_fa = cf.getGenomeFromENA(data_dir, species, assembly, False)
    
    #2. Register the data with the DMP
    from dmp import dmp
    
    da = dmp()
    
    print da.get_files_by_user("test")
    
    genome_file = da.set_file("test", genome_fa, "fasta", "Assembly", 9606, None)
    file_in = da.set_file("test", file_loc, "fasta", "ChIP-seq", 9606, None)
    file_bg_in = da.set_file("test", file_bg_loc, "fasta", "ChIP-seq", 9606, None)
    
    print da.get_files_by_user("test")
    
    # 3. Instantiate and launch the App
    from nnn import WorkflowApp
    app = WoekflowApp()
    results = app.launch(process_chipseq, [genome_file, file_in, file_bg_in], {})
    
    print da.get_files_by_user("test")
    
