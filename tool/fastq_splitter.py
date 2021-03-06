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

import os
import shlex
import subprocess
import shutil
import sys
import re
import tarfile
import multiprocessing

from utils import logger

try:
    if hasattr(sys, '_run_from_cmdl') is True:
        raise ImportError
    from pycompss.api.parameter import FILE_IN, FILE_OUT, IN, OUT
    from pycompss.api.task import task
    # from pycompss.api.api import compss_wait_on
except ImportError:
    logger.warn("[Warning] Cannot import \"pycompss\" API packages.")
    logger.warn("          Using mock decorators.")

    from utils.dummy_pycompss import FILE_IN, FILE_OUT, IN, OUT  # pylint: disable=ungrouped-imports
    from utils.dummy_pycompss import task  # pylint: disable=ungrouped-imports
    # from utils.dummy_pycompss import compss_wait_on  # pylint: disable=ungrouped-imports

from basic_modules.tool import Tool
from basic_modules.metadata import Metadata

from tool.fastqreader import fastqreader


# ------------------------------------------------------------------------------

class fastq_splitter(Tool):
    """
    Script for splitting up FASTQ files into manageable chunks
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
        logger.info("FASTQ Splitter")
        Tool.__init__(self)

        if configuration is None:
            configuration = {}

        self.configuration.update(configuration)

    def _compress_file_mp(self, file_in):
        """
        Function to compress a given file using pigz. If pigz is not installed
        then gzip is used.

        Parameters
        ----------
        file_in : str
            Input file
        """
        try:
            command_line = 'pigz ' + file_in
            args = shlex.split(command_line)
            process = subprocess.Popen(args)
            process.wait()
        except OSError:
            logger.warn("OSERROR: pigz not installed, using gzip")
            command_line = 'gzip ' + file_in
            args = shlex.split(command_line)
            process = subprocess.Popen(args)
            process.wait()

    @task(
        in_file1=FILE_IN, tag=IN,
        out_file=FILE_OUT, files_out=OUT,
        returns=list)
    def single_splitter(self, in_file1, out_file, tag='tmp'):  # pylint: disable=no-self-use
        """
        Function to divide the FastQ files into separate sub files of 1000000
        sequences so that the aligner can run in parallel.

        Parameters
        ----------
        in_file1 : str
            Location of first FASTQ file
        tag : str
            DEFAULT = tmp
            Tag used to identify the files. Useful if this is getting run
            manually on a single machine multiple times to prevent collisions of
            file names. It is also the temporary directory used within the
            compressed out_file containing the separated and compressed FASTQ
            files.


        Returns
        -------
        Returns: Returns a list of the files that have been generated.
                 Each sub list containing the two paired end files for that
                 subset.
        paired_files : list
            List of lists of pair end files. Each sub list containing the two
            paired end files for that subset.
        """

        fqr = fastqreader()
        fqr.openFastQ(in_file1)
        fqr.createOutputFiles(tag)

        fastq_chunk_size = 1000000
        if "fastq_chunk_size" in self.configuration:
            fastq_chunk_size = self.configuration["fastq_chunk_size"]

        record1 = fqr.next(1)

        count_r3 = 0

        file_loc_1 = fqr.fastq1.split("/")
        file_loc_1[-1] = file_loc_1[-1].replace(
            ".fastq",
            "." + str(fqr.output_tag) + "_" + str(fqr.output_file_count) + ".fastq")
        file_loc_1.insert(-1, tag)

        files_out = [[file_loc_1[-1]]]

        while fqr.eof(1) is False:
            fqr.writeOutput(record1, 1)
            record1 = fqr.next(1)
            count_r3 += 1

            if count_r3 % fastq_chunk_size == 0:
                fqr.incrementOutputFiles()
                file_loc_1 = fqr.fastq1.split("/")
                new_suffix = "." + str(fqr.output_tag) + "_" + str(fqr.output_file_count) + ".fastq"
                file_loc_1[-1] = re.sub('.fastq$', new_suffix, file_loc_1[-1])
                file_loc_1.insert(-1, tag)

                files_out.append([file_loc_1[-1]])

        fqr.closeFastQ()
        fqr.closeOutputFiles()

        fqgz_files = []
        for fq_file in files_out:
            self._compress_file_mp("/".join(file_loc_1[:-1]) + '/' + fq_file[0])
            fqgz_files.append([fq_file[0] + ".gz"])

        untar_idx = True
        if "no-untar" in self.configuration and self.configuration["no-untar"] is True:
            untar_idx = False

        if untar_idx is True:
            output_file_pregz = out_file.replace('.tar.gz', '.tar')

            if os.path.isfile(out_file):
                os.remove(out_file)

            tar = tarfile.open(output_file_pregz, "w")
            tar.add("/".join(file_loc_1[:-1]), arcname=tag)
            tar.close()

            self._compress_file_mp(output_file_pregz)

            shutil.rmtree("/".join(file_loc_1[:-1]))

        return fqgz_files

    @task(
        in_file1=FILE_IN, in_file2=FILE_IN, tag=IN,
        out_file=FILE_OUT, files_out=OUT,
        returns=list)
    def paired_splitter(self, in_file1, in_file2, out_file, tag='tmp'):  # pylint: disable=no-self-use
        """
        Function to divide the paired-end FastQ files into separte sub files
        of 1000000 sequences so that the aligner can run in parallel.

        Parameters
        ----------
        in_file1 : str
            Location of first paired end FASTQ file
        in_file2 : str
            Location of second paired end FASTQ file
        tag : str
            DEFAULT = tmp
            Tag used to identify the files. Useful if this is getting run
            manually on a single machine multiple times to prevent collisions of
            file names. It is also the temporary directory used within the
            compressed out_file containing the separated and compressed FASTQ
            files.


        Returns
        -------
        Returns: Returns a list of lists of the files that have been generated.
                 Each sub list containing the two paired end files for that
                 subset.
        paired_files : list
            List of lists of pair end files. Each sub list containing the two
            paired end files for that subset.
        """

        fqr = fastqreader()
        fqr.openFastQ(in_file1, in_file2)
        fqr.createOutputFiles(tag)

        fastq_chunk_size = 1000000
        if "fastq_chunk_size" in self.configuration:
            fastq_chunk_size = self.configuration["fastq_chunk_size"]

        record1 = fqr.next(1)
        record2 = fqr.next(2)

        count_r1 = 0
        count_r2 = 0
        count_r3 = 0

        file_loc_1 = fqr.fastq1.split("/")
        new_suffix = "." + str(fqr.output_tag) + "_" + str(fqr.output_file_count) + ".fastq"
        file_loc_1[-1] = re.sub('.fastq$', new_suffix, file_loc_1[-1])
        file_loc_1.insert(-1, tag)

        file_loc_2 = fqr.fastq2.split("/")
        new_suffix = "." + str(fqr.output_tag) + "_" + str(fqr.output_file_count) + ".fastq"
        file_loc_2[-1] = re.sub('.fastq$', new_suffix, file_loc_2[-1])

        file_loc_2.insert(-1, tag)
        files_out = [[file_loc_1[-1], file_loc_2[-1]]]

        while fqr.eof(1) is False and fqr.eof(2) is False:
            r1_id = record1["id"].split(" ")
            r2_id = record2["id"].split(" ")

            if r1_id[0] == r2_id[0]:
                fqr.writeOutput(record1, 1)
                fqr.writeOutput(record2, 2)

                record1 = fqr.next(1)
                record2 = fqr.next(2)

                count_r1 += 1
                count_r2 += 1
                count_r3 += 1
            elif r1_id[0] < r2_id[0]:
                record1 = fqr.next(1)
                count_r1 += 1
            else:
                record2 = fqr.next(2)
                count_r2 += 1

            if count_r3 % fastq_chunk_size == 0:
                fqr.incrementOutputFiles()
                file_loc_1 = fqr.fastq1.split("/")
                new_suffix = "." + str(fqr.output_tag) + "_" + str(fqr.output_file_count) + ".fastq"
                file_loc_1[-1] = re.sub('.fastq$', new_suffix, file_loc_1[-1])
                file_loc_1.insert(-1, tag)

                file_loc_2 = fqr.fastq2.split("/")
                new_suffix = "." + str(fqr.output_tag) + "_" + str(fqr.output_file_count) + ".fastq"
                file_loc_2[-1] = re.sub('.fastq$', new_suffix, file_loc_2[-1])
                file_loc_2.insert(-1, tag)

                files_out.append([file_loc_1[-1], file_loc_2[-1]])

        fqr.closeFastQ()
        fqr.closeOutputFiles()

        fqgz_files = []
        for fq_file in files_out:
            fq_file_1 = "/".join(file_loc_1[:-1]) + '/' + fq_file[0]
            fq_file_2 = "/".join(file_loc_1[:-1]) + '/' + fq_file[1]

            f1_proc = multiprocessing.Process(
                name='fastq_1', target=self._compress_file_mp,
                args=(fq_file_1,)
            )
            f2_proc = multiprocessing.Process(
                name='fastq_2', target=self._compress_file_mp,
                args=(fq_file_2,)
            )

            f1_proc.start()
            f2_proc.start()

            f1_proc.join()
            f2_proc.join()

            fqgz_files.append([fq_file[0] + ".gz", fq_file[1] + ".gz"])

        output_file_pregz = out_file.replace('.tar.gz', '.tar')

        untar_idx = True
        if "no-untar" in self.configuration and self.configuration["no-untar"] is True:
            untar_idx = False

        if untar_idx is True:
            if os.path.isfile(out_file):
                os.remove(out_file)
            tar = tarfile.open(output_file_pregz, "w")
            tar.add("/".join(file_loc_1[:-1]), arcname=tag)
            tar.close()

            self._compress_file_mp(output_file_pregz)

            shutil.rmtree("/".join(file_loc_1[:-1]))

        return fqgz_files

    def run(self, input_files, input_metadata, output_files):
        """
        The main function to run the splitting of FASTQ files (single or
        paired) so that they can aligned in a distributed manner

        Parameters
        ----------
        input_files : dict
            List of input fastq file locations
        metadata : dict
        output_files : dict

        Returns
        -------
        output_file : str
            Location of compressed (.tar.gz) of the split FASTQ files
        output_names : list
            List of file names in the compressed file

        """

        sources = [input_files["fastq1"]]

        if "fastq2" in input_files:
            sources.append(input_files["fastq2"])
            self.paired_splitter(
                input_files["fastq1"], input_files["fastq2"],
                input_files["fastq1"] + ".tar.gz"
            )
        else:
            self.single_splitter(
                input_files["fastq1"],
                input_files["fastq1"] + ".tar.gz",
            )

        # results = compss_wait_on(results)

        fastq_tar_meta = Metadata(
            data_type=input_metadata["fastq1"].data_type,
            file_type="TAR",
            file_path=output_files["output"],
            sources=sources,
            taxon_id=input_metadata["fastq1"].taxon_id,
            meta_data={
                "tool": "fastq_splitter"
            }
        )

        return (
            {"output": input_files["fastq1"] + ".tar.gz"},
            {"output": fastq_tar_meta}
        )

# ------------------------------------------------------------------------------
