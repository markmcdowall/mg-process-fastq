#!/usr/bin/env python
#!/home/pmes/.pyenv/shims/python

# -*- coding: utf-8 -*-

from __future__ import print_function

import traceback
import os.path
import argparse
import sys
if '/opt/COMPSs/Bindings/python' in sys.path:
    sys.path.pop(sys.path.index('/opt/COMPSs/Bindings/python'))
import tarfile
import multiprocessing
import json
import shutil
from random import random
from string import ascii_letters as letters

import collections
# Required for ReadTheDocs
from functools import wraps # pylint: disable=unused-import

from basic_modules.workflow import Workflow
from basic_modules.metadata import Metadata

from tool.tb_full_mapping import tbFullMappingTool
from tool.tb_parse_mapping import tbParseMappingTool
from tool.tb_filter import tbFilterTool

class ResultObj(dict):
    
    error = False
    metadata = {}
    
    def __init__(self,error,metadata):
        self.error = error
        self.metadata = metadata
        
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
class tadbit_map_parse_filter(Workflow):
    
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
        tool_extra_config = json.load(file((__file__).replace('.py','_config.json')))
        os.environ["PATH"] += os.pathsep + convert_from_unicode(tool_extra_config["bin_path"])
        
        if configuration is None:
            configuration = {}

        self.configuration.update(convert_from_unicode(configuration))
        
        if 'mapping:refGenome' in self.configuration:
            self.configuration['mapping_refGenome'] = self.configuration['mapping:refGenome']
        if 'parsing:refGenome' in self.configuration:
            self.configuration['parsing_refGenome'] = self.configuration['parsing:refGenome']
        self.configuration.update(
            {(key.split(':'))[-1]: val for key, val in self.configuration.items()}
        )
        if 'filters' in self.configuration:
            self.configuration['filters'] = [int(f) for f in self.configuration['filters']]
        if 'windows' in self.configuration:
            if self.configuration['windows']:
                w1 = self.configuration['windows'].split(" ")
                self.configuration['windows'] = [tuple(map(int, x.split(':'))) for x in w1]
            else:
                self.configuration['windows'] = ''
        else:
            self.configuration['windows'] = ''

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
            List of locations for the output bam files
        """
        
        print(
            "PROCESS MAP - FILES PASSED TO TOOLS:",
            remap(input_files, "read1", "read2")
        )
        
        m_results_meta = {}
        m_results_files = {}

        try:
            if 'parsing:ref_genome_fasta' in input_files:
                genome_fa = convert_from_unicode(input_files['parsing:ref_genome_fasta'])
            elif 'parsing_refGenome' in self.configuration:
                genome_fa = self.configuration['public_dir']+convert_from_unicode(self.configuration['parsing_refGenome'])
                
            
            if 'mapping:ref_genome_gem' in input_files: 
                genome_gem = convert_from_unicode(input_files['mapping:ref_genome_gem'])
            elif 'mapping_refGenome' in self.configuration:
                genome_gem = self.configuration['public_dir']+convert_from_unicode(self.configuration['mapping_refGenome'])
            
            fastq_file_1 = convert_from_unicode(input_files['read1'])
            fastq_file_2 = convert_from_unicode(input_files['read2'])
            input_metadata = remap(self.configuration, "ncpus","iterative_mapping","workdir","windows",rest_enzyme="enzyme_name")
            input_metadata['quality_plot'] = True        
            
            tfm1 = tbFullMappingTool()
            tfm1_files, tfm1_meta = tfm1.run([genome_gem, fastq_file_1], [], input_metadata)
            
            tfm2 = tbFullMappingTool()
            tfm2_files, tfm2_meta = tfm2.run([genome_gem, fastq_file_2], [], input_metadata)
             
            tpm = tbParseMappingTool()
            files = [genome_fa] + tfm1_files[:-2] + tfm2_files[:-2]
     
            input_metadata = remap(self.configuration, "ncpus","chromosomes","workdir",rest_enzyme="enzyme_name")                        
            input_metadata['mapping'] = [tfm1_meta['func'], tfm2_meta['func']]
            input_metadata['expt_name'] = 'vre' 
             
              
            print("TB MAPPED FILES:", files)
            print("TB PARSE METADATA:", input_metadata)
            tpm_files, tpm_meta = tpm.run(files, [], input_metadata)
            
            if 'error' in tpm_meta:
                m_results_meta["paired_reads"] = Metadata(
                    data_type="hic_sequences",
                    file_type="BAM",
                    file_path=None,
                    source_id=None,
                    meta_data={
                        "tool": "tadbit",
                        "description": "Paired end reads",
                        "visible": True
                    },
                    data_id=None)
                m_results_meta["paired_reads"].error = True
                m_results_meta["paired_reads"].exception = tpm_meta['error']

                
            print("TB PARSED FILES:", tpm_files)
              
            input_metadata = remap(self.configuration,"root_dir", "ncpus", "chromosomes","workdir",'filters')
            if 'min_dist_RE' in self.configuration:
                input_metadata['min_dist_RE'] = self.configuration['min_dist_RE']
            if 'min_fragment_size' in self.configuration:
                input_metadata['min_fragment_size'] = self.configuration['min_fragment_size']
            if 'max_fragment_size' in self.configuration:
                input_metadata['max_fragment_size'] = self.configuration['max_fragment_size']
            input_metadata['expt_name'] = 'vre'
            input_metadata['outbam'] = 'paired_reads'
            input_metadata['root_dir'] = input_metadata['root_dir'] +'/' + self.configuration['project'] 
            input_metadata['custom_filter'] = True
            input_metadata['histogram'] = True
              
            tbf = tbFilterTool()
            tf_files, tf_meta = tbf.run(tpm_files, [], input_metadata)
        
              
            print("TB FILTER FILES:", tf_files[0])
               
            
            m_results_files["paired_reads"] = tf_files[0]+'.bam'
            m_results_files["map_parse_filter_stats"] = self.configuration['root_dir']+'/' + self.configuration['project']+"/map_parse_filter_stats.tar.gz"
              
            with tarfile.open(m_results_files["map_parse_filter_stats"], "w:gz") as tar:
                tar.add(tfm1_files[-1],arcname=os.path.basename(tfm1_files[-1]))
                tar.add(tfm1_files[-2],arcname=os.path.basename(tfm1_files[-2]))
                tar.add(tfm2_files[-1],arcname=os.path.basename(tfm2_files[-1]))
                tar.add(tfm2_files[-2],arcname=os.path.basename(tfm2_files[-2]))
                tar.add(tf_files[-1],arcname=os.path.basename(tf_files[-1]))
                tar.add(tf_files[-2],arcname=os.path.basename(tf_files[-2]))
             
             
             # List of files to get saved
            print("TADBIT RESULTS:", m_results_files)
            
            
            m_results_meta["paired_reads"] = Metadata(
                    data_type="hic_sequences",
                    file_type="BAM",
                    file_path=m_results_files["paired_reads"],
                    source_id=[""],
                    meta_data={
                        "description": "Paired end reads",
                        "visible": True,
                        "assembly": "",
                        "func" : tfm1_meta['func']
                    },
                    data_id=None,
                    taxon_id=self.configuration["taxon_id"])
            
            m_results_meta["map_parse_filter_stats"] = Metadata(
                    data_type="tool_statistics",
                    file_type="TAR",
                    file_path=m_results_files["map_parse_filter_stats"],
                    source_id=[""],
                    meta_data={
                        "description": "TADbit mapping, parsing and filtering statistics",
                        "visible": True
                    },
                    data_id=None)
        except Exception as e:
            m_results_meta["paired_reads"] = Metadata(
                    data_type="hic_sequences",
                    file_type="BAM",
                    file_path=None,
                    source_id=[""],
                    meta_data={
                        "description": "Paired end reads",
                        "visible": True
                    },
                    data_id=None)
            m_results_meta["paired_reads"].error = True
            m_results_meta["paired_reads"].exception = str(e)

            
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
 
def main(args, num_cores):
    
    # 1. Instantiate and launch the App
    print("1. Instantiate and launch the App")
    from apps.workflowapp import WorkflowApp
    app = WorkflowApp()
    root_dir = args.root_dir
    
    print ("0) Unpack information from JSON")
    input_IDs, arguments, output_files = _read_config(
        args.config)

    input_metadata_IDs, taxon_id = _read_metadata(
        args.metadata)

    # arrange by role
    input_metadata = {}
    for role, ID in input_IDs.items():
        input_metadata[role] = input_metadata_IDs[ID]

    # get paths from IDs
    input_files = {}
    for role, metadata in input_metadata.items():
        input_files[role] = metadata.file_path

    input_files = make_absolute_path(input_files, root_dir)
    
    tmp_name = ''.join([letters[int(random()*52)]for _ in xrange(5)])
    workdir = os.path.dirname(os.path.abspath(args.out_metadata))+'/_tmp_tadbit_'+tmp_name
    if not os.path.exists(workdir):
        os.makedirs(workdir)
    arguments.update({"ncpus":num_cores, "root_dir": args.root_dir, "public_dir": args.public_dir, "workdir": workdir, "taxon_id":taxon_id})
    output_files, output_metadata = app.launch(tadbit_map_parse_filter, input_files, input_metadata, output_files, arguments, )

    print("4) Pack information to JSON")
    #cleaning
    clean_temps(workdir)
    
    return _write_json(
        input_files, input_metadata,
        output_files, output_metadata,
        args.out_metadata)
    
    
    
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

def make_absolute_path(files, root):
    """Make paths absolute."""
    for role, path in files.items():
        files[role] = os.path.join(root, path)
    return files

def _read_config(json_path):
    """
    Read config.json to obtain:
    input_IDs: dict containing IDs of tool input files
    arguments: dict containing tool arguments
    output_files: dict containing absolute paths of tool outputs

    For more information see the schema for config.json.
    """
    configuration = json.load(file(json_path))
    input_IDs = {}
    for input_ID in configuration["input_files"]:
        input_IDs[input_ID["name"]] = input_ID["value"]

    output_files = {}
    if "output_files" in configuration:
        for output_file in configuration["output_files"]:
            output_files[output_file["name"]] = output_file["file"]

    arguments = {}
    for argument in configuration["arguments"]:
        arguments[argument["name"]] = argument["value"]

    return input_IDs, arguments, output_files

def _read_metadata(json_path):
    """
    Read input_metadata.json to obtain input_metadata_IDs, a dict
    containing metadata on each of the tool input files,
    arranged by their ID.

    For more information see the schema for input_metadata.json.
    """
    metadata = json.load(file(json_path))
    input_metadata = {}
    for input_file in metadata:
        input_metadata[input_file["_id"]] = Metadata(
            data_type=input_file["data_type"],
            file_type=input_file["file_type"],
            file_path=input_file["file_path"],
            source_id=input_file["source_id"],
            meta_data=input_file["meta_data"],
            data_id=input_file["_id"])
    taxon_id =  metadata[0]["taxon_id"]
    return input_metadata, taxon_id

def _write_json(
                input_files, input_metadata,
                output_files, output_metadata, json_path):
    """
    Write results.json using information from input_files and output_files:
    input_files: dict containing absolute paths of input files
    input_metadata: dict containing metadata on input files
    output_files: dict containing absolute paths of output files
    output_metadata: dict containing metadata on output files

    For more information see the schema for results.json.
    """
    results = []
    for role, path in output_files.items():
        results.append({
            "name": role,
            "file_path": path,
            "data_type": output_metadata[role].data_type,
            "file_type": output_metadata[role].file_type,
            "source_id": output_metadata[role].source_id,
            "taxon_id": output_metadata[role].taxon_id,
            "meta_data": output_metadata[role].meta_data
        })
    json.dump({"output_files": results}, file(json_path, 'w'))
    return True
    
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    sys._run_from_cmdl = True

    # Set up the command line parameters
    parser = argparse.ArgumentParser(description="TADbit map")
    # Config file
    parser.add_argument("--config", help="Configuration JSON file", 
                        type=CommandLineParser.valid_file, metavar="config", required=True)
    # Root dir
    parser.add_argument("--root_dir", help="Working directory",
                        type=CommandLineParser.valid_file, metavar="root_dir", required=True)
    # Public dir
    parser.add_argument("--public_dir", help="Public directory to upload the results",
                        metavar="public_dir", required=True)
    # Metadata
    parser.add_argument("--metadata", help="Project metadata", metavar="metadata", required=True)
    # Output metadata
    parser.add_argument("--out_metadata", help="Output metadata", metavar="output_metadata", required=True)

    args = parser.parse_args()

    # Number of cores available
    num_cores = multiprocessing.cpu_count()

    RESULTS = main(args, num_cores)
    
    print(RESULTS)