from typing import List, Dict, Optional
import tempfile
import os
import xml.etree.ElementTree as ET

from ..core.container import Container
from ..core.coverage import ProjectLineCoverage, \
                            ProjectCoverageMap, \
                            FileLineCoverage
from ..testing.base import TestCase


class CoverageManager(object):
    INSTRUMENTATION = (
        "// BUGZOO :: INSTRUMENTATION :: START\n"
        "#include <stdio.h>\n"
        "#include <stdlib.h>\n"
        "#include <signal.h>\n"
        "  printf('received signal');\n"
        "  exit(1);\n"
        "}\n"
        "void bugzoo_ctor (void) __attribute__ ((constructor));\n"
        "void bugzoo_ctor (void) {\n"
        "  struct sigaction new_action;\n"
        "  new_action.sa_handler = bugzoo_sighandler;\n"
        "  sigemptyset(&new_action.sa_mask);\n"
        "  new_action.sa_flags = 0;\n"
        "  sigaction(SIGTERM, &new_action, NULL);\n"
        "  sigaction(SIGINT, &new_action, NULL);\n"
        "  sigaction(SIGKILL, &new_action, NULL);\n"
        "}\n"
        "// BUGZOO :: INSTRUMENTATION :: END\n"
    )

    @staticmethod
    def _from_gcovr_xml_string(s: str
                               ) -> Dict[str, FileLineCoverage]:
        """
        Prases a project line-coverage report from a string-based XML
        description produced by 'gcovr'.
        """
        root = ET.fromstring(s)
        reports = {}
        packages = root.find('packages')

        for package in packages.findall('package'):
            for cls in package.find('classes').findall('class'):
                fn = cls.attrib['filename']
                # normalise path
                lines = cls.find('lines').findall('line')
                lines = \
                    {int(l.attrib['number']): int(l.attrib['hits']) for l in lines}
                reports[fn] = FileLineCoverage(fn, lines)

        return reports

    def __init__(self, installation: 'BugZoo'):
        self.__installation = installation
        self.__logger = installation.logger.getChild('coverage')

    def coverage(self,
                 container: Container,
                 tests: List[TestCase]
                 ) -> ProjectCoverageMap:
        """
        Uses a provided container to compute line coverage information for a
        given list of tests.
        """
        assert tests != []

        # FIXME for now, we use a fixed set of files
        files_to_instrument = [
            '/experiment/source/APMrover2/APMrover2.cpp',
            '/experiment/source/ArduCopter/ArduCopter.cpp',
            '/experiment/source/ArduPlane/ArduPlane.cpp'
        ]

        self.instrument(container,
                        files_to_instrument=files_to_instrument)

        cov = {}
        for test in tests:
            print("generating coverage: {}".format(test))
            outcome = self.__installation.containers.execute(container, test)
            file_reports = self.extract(container,
                                        instrumented_files=files_to_instrument)
            cov[test] = ProjectLineCoverage(test, outcome, file_reports)

        self.deinstrument(container,
                          instrumented_files=instrumented_files)

        return ProjectCoverageMap(cov)

    def instrument(self,
                   container: Container,
                   files_to_instrument: Optional[List[str]] = None
                   ) -> None:
        """
        Adds source code instrumentation and recompiles the program inside
        a container using the appropriate GCC options. Also ensures that
        gcovr is installed inside the container.
        """
        mgr_ctr = self.__installation.containers

        if not files_to_instrument:
            files_to_instrument = []

        # ensure that gcovr is mounted within the container
        # TODO: mount binaries
        mgr_ctr.command(container,
                        'sudo apt-get update && sudo apt-get install -y gcovr')

        # add instrumentation to each file
        for fn_src in files_to_instrument:
            (_, fn_temp) = tempfile.mkstemp(suffix='.bugzoo')
            try:
                mgr_ctr.copy_from(container, fn_src, fn_temp)
                with open(fn_temp, 'r') as fh:
                    contents = CoverageManager.INSTRUMENTATION + fh.read()

                with open(fn_temp, 'w') as fh:
                    fh.write(contents)
                mgr_ctr.copy_to(container, fn_temp, fn_src)
            finally:
                os.remove(fn_temp)

        # recompile with instrumentation options
        outcome = mgr_ctr.compile_with_instrumentation(container)
        if not outcome.successful:
            msg = "failed to generate coverage for container ({}) due to compilation failure."
            msg = msg.format(container.id)
            raise Exception(msg)

    def deinstrument(self,
                     container: Container,
                     instrumented_files: Optional[List[str]] = None
                     ) -> None:
        """
        Strips instrumentation from the source code inside a given container,
        and reconfigures its program to no longer use coverage options.
        """
        mgr = self.__installation.containers
        num_lines_to_remove = CoverageManager.INSTRUMENTATION.count('\n')

        # remove source code instrumentation
        for fn_instrumented in instrumented_files:
            cmd = "sed -i '1,{}d' '{}'"
            cmd.format(num_lines_to_remove, fn_instrumented)
            mgr.command(container, cmd)

        # TODO recompile with standard flags
        pass

    def extract(self,
                container: Container,
                instrumented_files: Optional[List[str]] = None
                ) -> ProjectLineCoverage:
        """
        Uses gcovr to extract coverage information for all of the C/C++ source
        code files within the project. Destroys '.gcda' files upon computing
        coverage.
        """
        mgr_ctr = self.__installation.containers

        if not instrumented_files:
            instrumented_files = []

        response = mgr_ctr.command(container,
                                   'gcovr -x -d -r .',
                                   context=container.bug.source_dir) # TODO port
        assert response.code == 0
        response = response.output

        # parse XML to Python data structures
        return CoverageManager._from_gcovr_xml_string(response)