"""
.. See the NOTICE file distributed with this work for additional information
   regarding copyright ownership.

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

from __future__ import print_function

import shlex
import subprocess
import itertools
import sys
import os

from utils import logger

try:
    if hasattr(sys, '_run_from_cmdl') is True:
        raise ImportError
    from pycompss.api.parameter import FILE_IN, FILE_OUT
    from pycompss.api.task import task
    # from pycompss.api.api import compss_wait_on
except ImportError:
    logger.warn("[Warning] Cannot import \"pycompss\" API packages.")
    logger.warn("          Using mock decorators.")

    from utils.dummy_pycompss import FILE_IN, FILE_OUT  # pylint: disable=ungrouped-imports
    from utils.dummy_pycompss import task  # pylint: disable=ungrouped-imports
    # from utils.dummy_pycompss import compss_wait_on  # pylint: disable=ungrouped-imports

from basic_modules.tool import Tool
from basic_modules.metadata import Metadata

# ------------------------------------------------------------------------------


class kallistoQuantificationTool(Tool):
    """
    Tool for quantifying RNA-seq alignments to calculate expression levels of
    genes within a genome.
    """

    def __init__(self, configuration=None):
        """
        Initialise the tool with its configuration.


        Parameters
        ----------
        configuration : dict
            a dictionary containing parameters that define how the operation
            should be carried out, which are specific to each Tool.
        """
        logger.info("Kallisto Quantification")
        Tool.__init__(self)

        if configuration is None:
            configuration = {}

        self.configuration.update(configuration)

    @task(
        cdna_idx_file=FILE_IN,
        fastq_file_loc=FILE_IN,
        abundance_h5_file=FILE_OUT,
        abundance_tsv_file=FILE_OUT,
        run_info_file=FILE_OUT)
    def kallisto_quant_single(  # pylint: disable=too-many-arguments, too-many-locals
            self, cdna_idx_file, fastq_file_loc,
            abundance_h5_file, abundance_tsv_file, run_info_file):
        """
        Kallisto quantifier for single end RNA-seq data

        Parameters
        ----------
        idx_loc : str
            Location of the output index file
        fastq_file_loc : str
            Location of the FASTQ sequence file

        Returns
        -------
        wig_file_loc : loc
            Location of the wig file containing the levels of expression
        """

        fq_stats = self.seq_read_stats(fastq_file_loc)

        output_dir = fastq_file_loc.split('/')

        std = fq_stats["std"]
        if std == 0.0:
            std = 1/fq_stats['mean']

        command_line = "kallisto quant -i " + cdna_idx_file + " "
        command_line += " -o " + "/".join(output_dir[0:-1]) + "/"
        command_line += " --single -l " + str(fq_stats['mean']) + " "
        command_line += "-s " + str(std) + " " + fastq_file_loc

        logger.info("KALLISTO_QUANT COMMAND", command_line)

        args = shlex.split(command_line)
        process = subprocess.Popen(args)
        process.wait()

        output_files = [
            {
                "in": '/'.join(output_dir[0:-1]) + "/abundance.h5",
                "out": abundance_h5_file
            },
            {
                "in": '/'.join(output_dir[0:-1]) + "/abundance.tsv",
                "out": abundance_tsv_file
            },
            {
                "in": '/'.join(output_dir[0:-1]) + "/run_info.json",
                "out": run_info_file
            }
        ]

        for i in output_files:
            if i["in"] != i["out"]:
                if os.path.isfile(i["in"]) is True and os.path.getsize(i["in"]) > 0:
                    with open(i["out"], "wb") as f_out:
                        with open(i["in"], "rb") as f_in:
                            f_out.write(f_in.read())
                else:
                    with open(i["out"], "w") as f_out:
                        f_out.write("")

        return True

    @task(
        fastq_file_loc_01=FILE_IN,
        fastq_file_loc_02=FILE_IN,
        cdna_idx_file=FILE_IN,
        abundance_h5_file=FILE_OUT,
        abundance_tsv_file=FILE_OUT,
        run_info_file=FILE_OUT)
    def kallisto_quant_paired(  # pylint disable=no-self-use
            self, cdna_idx_file, fastq_file_loc_01, fastq_file_loc_02,
            abundance_h5_file, abundance_tsv_file, run_info_file):
        """
        Kallisto quantifier for paired end RNA-seq data

        Parameters
        ----------
        idx_loc : str
            Location of the output index file
        fastq_file_loc_01 : str
            Location of the FASTQ sequence file
        fastq_file_loc_02 : str
            Location of the paired FASTQ sequence file

        Returns
        -------
        wig_file_loc : loc
            Location of the wig file containing the levels of expression
        """

        output_dir = fastq_file_loc_01.split('/')

        command_line = 'kallisto quant -i ' + cdna_idx_file + ' '
        command_line += '-o ' + '/'.join(output_dir[0:-1]) + "/ "
        command_line += fastq_file_loc_01 + ' ' + fastq_file_loc_02

        args = shlex.split(command_line)
        process = subprocess.Popen(args)
        process.wait()

        output_files = [
            {
                "in": '/'.join(output_dir[0:-1]) + "/abundance.h5",
                "out": abundance_h5_file
            },
            {
                "in": '/'.join(output_dir[0:-1]) + "/abundance.tsv",
                "out": abundance_tsv_file
            },
            {
                "in": '/'.join(output_dir[0:-1]) + "/run_info.json",
                "out": run_info_file
            }
        ]

        for i in output_files:
            if os.path.isfile(i["in"]) is True and os.path.getsize(i["in"]) > 0:
                with open(i["out"], "wb") as f_out:
                    with open(i["in"], "rb") as f_in:
                        f_out.write(f_in.read())
            else:
                with open(i["out"], "w") as f_out:
                    f_out.write("")

        return True

    @staticmethod
    def seq_read_stats(file_in):
        """
        Calculate the mean and standard deviation of the reads in a fastq file

        Parameters
        ----------
        file_in : str
            Location of a FASTQ file

        Returns
        -------
        dict
            mean : Mean length of sequenced strands
            std  : Standard deviation of lengths of sequenced strands

        """

        from numpy import std
        from numpy import mean

        total_len = []
        with open(file_in, 'r') as file_handle:
            forthlines = itertools.islice(file_handle, 1, None, 4)
            for line in forthlines:
                line = line.rstrip()
                total_len.append(len(line))

        length_sd = std(total_len)
        length_mean = mean(total_len)

        return {'mean': length_mean, 'std': length_sd}

    def run(self, input_files, input_metadata, output_files):
        """
        Tool for calculating the level of expression

        Parameters
        ----------
        input_files : list
            Kallisto index file for the
            FASTQ file for the experiemtnal alignments
        input_metadata : list

        Returns
        -------
        array : list
            First element is a list of the index files. Second element is a
            list of the matching metadata
        """

        # input and output share most metadata
        output_metadata = {}

        # file_loc = input_files[1].split("/")
        # output_dir = "/".join(file_loc[0:-1])

        # abundance_h5_file = output_dir + "/abundance.h5"
        # abundance_tsv_file = output_dir + "/abundance.tsv"
        # run_info_file = output_dir + "/run_info.json"

        if "fastq2" not in input_files:
            self.kallisto_quant_single(
                input_files["index"], input_files["fastq1"],
                output_files["abundance_h5_file"], output_files["abundance_tsv_file"],
                output_files["run_info_file"]
            )
            # results = compss_wait_on(results)
        elif "fastq2" in input_files:
            # handle error
            self.kallisto_quant_paired(
                input_files["index"], input_files["fastq1"], input_files["fastq2"],
                output_files["abundance_h5_file"], output_files["abundance_tsv_file"],
                output_files["run_info_file"]
            )
            # results = compss_wait_on(results)
        else:
            return ({}, {})

        output_metadata = {
            "abundance_h5_file": Metadata(
                data_type="data_ranseq",
                file_type="hdf5",
                file_path=output_files["abundance_h5_file"],
                sources=[input_metadata["cdna"].file_path, input_metadata["fastq1"].file_path],
                taxon_id=input_metadata["cdna"].taxon_id,
                meta_data={
                    "assembly": input_metadata["cdna"].meta_data["assembly"],
                    "tool": "kallisto_quant"
                }
            ),
            "abundance_tsv_file": Metadata(
                data_type="data_ranseq",
                file_type="tsv",
                file_path=output_files["abundance_tsv_file"],
                sources=[input_metadata["cdna"].file_path, input_metadata["fastq1"].file_path],
                taxon_id=input_metadata["cdna"].taxon_id,
                meta_data={
                    "assembly": input_metadata["cdna"].meta_data["assembly"],
                    "tool": "kallisto_quant"
                }
            ),
            "run_info_file": Metadata(
                data_type="data_ranseq",
                file_type="tsv",
                file_path=output_files["run_info_file"],
                sources=[input_metadata["cdna"].file_path, input_metadata["fastq1"].file_path],
                taxon_id=input_metadata["cdna"].taxon_id,
                meta_data={
                    "assembly": input_metadata["cdna"].meta_data["assembly"],
                    "tool": "kallisto_quant"
                }
            )
        }

        return (output_files, output_metadata)

# ------------------------------------------------------------------------------
