from typing import List, Dict, Iterator
from bugzoo.coverage.base import ProjectCoverageMap, \
                                 FileLine


class LineSpectra(object):
    """
    Summarises the coverage information for a single line in the program in
    terms of the number of passing and failing tests that do and do not
    cover it, respectively.
    """
    def __init__(self, ep: int, ef: int, np: int, nf: int) -> None:
        assert ep >= 0
        assert ef >= 0
        assert np >= 0
        assert nf >= 0

        self.__ep = ep
        self.__ef = ef
        self.__np = np
        self.__nf = nf

    @property
    def ep(self) -> int:
        """
        The number of passing tests that cover this line.
        """
        return self.__ep

    @property
    def ef(self) -> int:
        """
        The number of failing tests that cover this line.
        """
        return self.__ef

    @property
    def np(self) -> int:
        """
        The number of passing tests that do not cover this line.
        """
        return self.__np

    @property
    def nf(self) -> int:
        """
        The number of failing tests that do not cover this line.
        """
        return self.__nf


class Spectra(object):
    @staticmethod
    def from_coverage(coverage: ProjectCoverageMap) -> 'Spectra':
        # tally the number of times that each line is touched by a passing
        # or failing test
        tally_failing: Dict[FileLine, int] = {}
        tally_passing: Dict[FileLine, int] = {}

        for test in coverage.passing:
            for line in coverage[test].lines:
                tally_passing[line] = tally_passing.get(line, 1)

        for test in coverage.failing:
            for line in coverage[test].lines:
                tally_failing[line] = tally_failing.get(line, 1)

        return Spectra(len(coverage.passing),
                       len(coverage.failing),
                       FileLine.compactify(tally_passing),
                       FileLine.compactify(tally_failing))

    def __init__(self,
                 num_passing: int,
                 num_failing: int,
                 tally_passing: Dict[str, Dict[int, int]],
                 tally_failing: Dict[str, Dict[int, int]]
                 ) -> None:
        self.__num_passing = num_passing
        self.__num_failing = num_failing
        self.__tally_passing = tally_passing
        self.__tally_failing = tally_failing

    def __getitem__(self, line: FileLine) -> LineSpectra:
        """
        Retrieves the spectra information for a given line.
        """
        if not line.filename in self.__tally_passing:
            ep = 0
        else:
            ep = self.__tally_passing[line.filename].get(line.num, 0)

        if not line.filename in self.__tally_failing:
            ef = 0
        else:
            ef = self.__tally_failing[line.filename].get(line.num, 0)

        np = self.__num_passing - ep
        nf = self.__num_failing - ef

        return LineSpectra(ep, ef, np, nf)

    def __iter__(self) -> Iterator[FileLine]:
        passing_lines = \
            set(FileLine.decompactify(self.__tally_passing).keys())
        failing_lines = \
            set(FileLine.decompactify(self.__tally_failing).keys())
        lines = passing_lines.union(failing_lines)
        for line in lines:
            yield line