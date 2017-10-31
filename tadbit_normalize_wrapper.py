#!/usr/bin/env python
#!/home/pmes/.pyenv/shims/python

# -*- coding: utf-8 -*-

from __future__ import print_function

import os.path
import argparse
import sys
import json
import multiprocessing
from random import random
from pysam                                import AlignmentFile
from string import ascii_letters as letters

import collections
import tarfile
# Required for ReadTheDocs
from functools import wraps # pylint: disable=unused-import

from basic_modules.workflow import Workflow
from basic_modules.metadata import Metadata

from tool.tb_normalize import tbNormalizeTool

class CommandLineParser(object):
    """Parses command line"""
    @staticmethod
    def valid_file(file_name):
        if not os.path.exists(file_name):
            raise argparse.ArgumentTypeError("The file does not exist")
        return file_name
    
    @staticmethod
    def valid_integer_number(ivalue):
        try:
            ivalue = int(ivalue)
        except:
            raise argparse.ArgumentTypeError("%s is an invalid value" % ivalue)
        if ivalue <= 0:
            raise argparse.ArgumentTypeError("%s is an invalid value" % ivalue)
        return ivalue
# ------------------------------------------------------------------------------
class tadbit_normalize(Workflow):
    
    configuration = {}

    def __init__(self, configuration=None):
        """
        Initialise the tool with its configuration.


        Parameters
        ----------
        configuration : dict
            a dictionary containing parameters that define how the operation
            should be carried out, which are specific to each Tool.
        """
        tool_extra_config = json.load(file(os.path.dirname(os.path.abspath(__file__))+'/tadbit_wrappers_config.json'))
        os.environ["PATH"] += os.pathsep + convert_from_unicode(tool_extra_config["bin_path"])
        
        if configuration is None:
            configuration = {}

        self.configuration.update(convert_from_unicode(configuration))
        
        # Number of cores available
        num_cores = multiprocessing.cpu_count()
        self.configuration["ncpus"] = num_cores
        
        tmp_name = ''.join([letters[int(random()*52)]for _ in xrange(5)])
        self.configuration['workdir'] = self.configuration['project']+'/_tmp_tadbit_'+tmp_name
        if not os.path.exists(self.configuration['workdir']):
            os.makedirs(self.configuration['workdir'])
            
        self.configuration.update(
            {(key.split(':'))[-1]: val for key, val in self.configuration.items()}
        )

    def run(self, input_files,metadata, output_files):
        """
        Parameters
        ----------
        files_ids : list
            List of file locations
        metadata : list
            Required meta data
        output_files : list
            List of output file locations

        Returns
        -------
        outputfiles : list
            List of locations for the output files
        """
        
        print(
            "PROCESS NORMALIZE - FILES PASSED TO TOOLS:",
            remap(input_files, "bamin")
        )
        
        
        bamin = convert_from_unicode(input_files['bamin'])
        input_metadata = remap(self.configuration, "resolution","min_perc","workdir", "max_perc", "ncpus")
        
        bamfile = AlignmentFile(bamin, 'rb')
        if len(bamfile.references) == 1:
            input_metadata["min_count"] = "10"
        bamfile.close()
            
        m_results_meta = {}
        
        tn = tbNormalizeTool()
        tn_files, tn_meta = tn.run([bamin], [], input_metadata)
        
        m_results_files = {}
        try:
            m_results_files["hic_biases"] = self.configuration['project']+"/"+os.path.basename(tn_files[0])
            os.rename(tn_files[0], m_results_files["hic_biases"])
        except:
            pass
        
        m_results_files["normalize_stats"] = self.configuration['project']+"/normalize_stats.tar.gz"
          
        with tarfile.open(m_results_files["normalize_stats"], "w:gz") as tar:
            tar.add(tn_files[1],arcname=os.path.basename(tn_files[1]))
            if len(tn_files) > 2:
                tar.add(tn_files[2],arcname=os.path.basename(tn_files[2]))
            
        # List of files to get saved
        print("TADBIT RESULTS:", m_results_files)

        m_results_meta["hic_biases"] = Metadata(
                data_type="hic_biases",
                file_type="PICKLE",
                file_path=m_results_files["hic_biases"],
                sources=[""],
                meta_data={
                    "description": "HiC biases for normalization",
                    "visible": True,
                    "assembly": ""
                },
                taxon_id=metadata['bamin'].taxon_id)
        m_results_meta["normalize_stats"] = Metadata(
                data_type="tool_statistics",
                file_type="TAR",
                file_path=m_results_files["normalize_stats"],
                sources=[""],
                meta_data={
                    "description": "TADbit normalize statistics",
                    "visible": True
                })
        
         
             
        #cleaning
        clean_temps(self.configuration['workdir']+"/04_normalization")
        clean_temps(self.configuration['workdir'])

        return m_results_files, m_results_meta
        
# ------------------------------------------------------------------------------

def remap(indict, *args, **kwargs):
    """
    Re-map keys of indict using information from arguments.
    Non-keyword arguments are keys of input dictionary that are passed
    unchanged to the output. Keyword arguments must be in the form
    old="new"
    and act as a translation table for new key names.
    """
    outdict = {role: indict[role] for role in args}
    outdict.update(
        {new: indict[old] for old, new in kwargs.items()}
    )
    return outdict
       
# ------------------------------------------------------------------------------

def convert_from_unicode(data):
    if isinstance(data, basestring):
        return str(data)
    elif isinstance(data, collections.Mapping):
        return dict(map(convert_from_unicode, data.iteritems()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(convert_from_unicode, data))
    else:
        return data
# ------------------------------------------------------------------------------

def main(args):
    
    from apps.jsonapp import JSONApp
    app = JSONApp()
    result = app.launch(tadbit_normalize,
                        args.config,
                        args.in_metadata,
                        args.out_metadata)
    
    
    return result
    
def clean_temps(working_path):
    """Cleans the workspace from temporal folder and scratch files"""
    for the_file in os.listdir(working_path):
        file_path = os.path.join(working_path, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            #elif os.path.isdir(file_path): shutil.rmtree(file_path)
        except:
            pass
    try:
        os.rmdir(working_path)
    except:
        pass
    print('[CLEANING] Finished')


# ------------------------------------------------------------------------------

if __name__ == "__main__":
    sys._run_from_cmdl = True

    # Set up the command line parameters
    parser = argparse.ArgumentParser(description="TADbit map")
    # Config file
    parser.add_argument("--config", help="Configuration JSON file", 
                        type=CommandLineParser.valid_file, metavar="config", required=True)

    # Metadata
    parser.add_argument("--in_metadata", help="Project metadata", metavar="in_metadata", required=True)
    # Output metadata
    parser.add_argument("--out_metadata", help="Output metadata", metavar="output_metadata", required=True)
    # Log file
    parser.add_argument("--log_file", help="Log file", metavar="log_file", required=True)

    args = parser.parse_args()

    RESULTS = main(args)
    
    print(RESULTS)
    