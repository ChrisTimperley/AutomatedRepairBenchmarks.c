from bugzoo.container import Container
from bugzoo.coverage.base import ProjectLineCoverage


class CoverageExtractor(object):
    """
    Coverage extractors are responsible for obtaining coverage information
    for a given program within a container. It is the responsibilty of the
    extractor to account for the language used by the program being studied.
    """
    def _prepare(self,
                container: Container
                ) -> None:
        """
        Prepares a given container such that it is able to
        """
        raise NotImplementedError

    def _extract(self,
                container: Container
                ) -> ProjectLineCoverage:
        """
        Extracts coverage information from the relevant coverage files within
        a given container.
        """
        raise NotImplementedError

    def collect(self,
                container: Container,
                test: TestCase
                ) -> ProjectLineCoverage:
        """
        Uses this coverage extractor to compute line coverage information for
        a given test.
        """
        self._prepare(container)
        container.execute(test)
        return self._extract(container)