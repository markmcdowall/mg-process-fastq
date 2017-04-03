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

import os, shutil, shlex, subprocess

try:
    from pycompss.api.parameter import FILE_IN, FILE_OUT
    from pycompss.api.task import task
except ImportError :
    print "[Warning] Cannot import \"pycompss\" API packages."
    print "          Using mock decorators."
    
    from dummy_pycompss import *

from basic_modules.metadata import Metadata
from basic_modules.tool import Tool

from common import common

pwd = os.environ.get('PWD')
pwd_split = pwd.split('/')

#if pwd_split[-1] != 'docs':
#    on_rtd = os.environ.get('READTHEDOCS') == 'True'
#    if on_rtd == False:
#        from bs_index.wg_build import *

# ------------------------------------------------------------------------------

class bssAlignerTool(Tool):
    """
    Script from BS-Seeker2 for building the index for alignment. In this case
    it uses Bowtie2.
    """
    
    def __init__(self):
        """
        Init function
        """
        print "BS-Seeker Aligner"

    @task(input_fastq1 = FILE_IN, input_fastq2 = FILE_IN, aligner = IN, aligner_path = IN,
        bss_path = IN,
        genome_fasta = FILE_IN, bam_out = FILE_INOUT, bt2_1 = FILE_IN, bt2_2 = FILE_IN,
        bt2_3 = FILE_IN, bt2_4 = FILE_IN, bt2_rev_1 = FILE_IN, bt2_rev_2 = FILE_IN)
    def bs_seeker_aligner(self, input_fastq1, input_fastq2, aligner, aligner_path, bss_path,
        genome_fasta, bam_out, bt2_1, bt2_2, bt2_3, bt2_4, bt2_rev_1, bt2_rev_2):
        """
        Alignment of the paired ends to the reference genome
        
        Generates bam files for the alignments
        
        This is performed by running the external program rather than
        reimplementing the code from the main function to make it easier when
        it comes to updating the changes in BS-Seeker2

        Parameters
        ----------
        input_fastq1 : str
            Location of paired end FASTQ file 
        input_fastq2 : str
            Location of paired end FASTQ file 2
        aligner : str
            Aligner to use
        aligner_path : str
            Location of the aligner
        genome_fasta : str
            Location of the genome FASTA file
        bam_out : str
            Location of the aligned bam file

        Returns
        -------
        bam_out : file
            Location of the BAM file generated during the alignment.
        """
        g_dir = genome_fasta.split("/")
        g_dir = "/".join(g_dir[0:-1])

        command_line = ("python " + bss_path + "/bs_seeker2-align.py"
            " --input_1 " + input_fastq1 + " --input_2 " + input_fastq2
            " --aligner " + aligner + " --path " + aligner_path
            " --genome " + genome_fasta + " -d " + g_dir
            " --bt2-p 4 -o " + bam_out).format()
        
        args = shlex.split(command_line)
        p = subprocess.Popen(args)
        p.wait()

        return True


    def run(self, input_files, metadata):
        """
        Tool for indexing the genome assembly using BS-Seeker2. In this case it
        is using Bowtie2
        
        Parameters
        ----------
        input_files : list
            FASTQ file
        metadata : list
        
        Returns
        -------
        array : list
            Location of the filtered FASTQ file
        """
        
        genome_fasta = input_files[0]
        fastq_file_1 = input_files[1]
        fastq_file_2 = input_files[2]
        output_file  = input_files[3]
        bt2_1        = input_files[4]
        bt2_2        = input_files[5]
        bt2_3        = input_files[6]
        bt2_4        = input_files[7]
        bt2_rev_1    = input_files[8]
        bt2_rev_2    = input_files[9]

        aligner      = metadata['aligner']
        aligner_path = metadata['aligner_path']
        bss_path     = metadata['bss_path']

        # input and output share most metadata
        output_metadata = {}
        
        # handle error                input_fastq1, input_fastq2, aligner, aligner_path, genome_fasta, bam_out
        if not self.bs_seeker_aligner(fastq_file_1, fastq_file_2, aligner, aligner_path, genome_fasta, output_file, bt2_1, bt2_2, bt2_3, bt2_4, bt2_rev_1, bt2_rev_2):
            output_metadata.set_exception(
                Exception(
                    "bs_seeker_aligner: Could not process files {}, {}.".format(*input_files)))
            output_file = None
        return ([output_file], output_metadata)

# ------------------------------------------------------------------------------