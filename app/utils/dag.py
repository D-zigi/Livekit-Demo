from typing import TypeVar, Union
from collections import defaultdict, deque

T = TypeVar("T", bound=Union[str, int])

class DirectedAcyclicGraph[T]:
    """
    A simple implementation of a directed acyclic graph (DAG) with topological sorting.
    """
    def __init__(self, nodes: list[T]):
        self.graph: dict[T, list[T]] = defaultdict(list[T])
        self.nodes = nodes

    def _get_predecessors(self, node: T) -> list[T]:
        """Returns the list of predecessor nodes for a given node."""
        return [source for source, targets in self.graph.items() if node in targets]

    def add_edge(self, source: T, target: T):
        """Adds a directed edge from source to target."""
        self.graph[source].append(target)

    def topo_sort(self) -> list[T]:
        """
        Performs topological sorting using Kahn's algorithm.
        """
        in_degree: dict[T, int] = { n: len(self._get_predecessors(n)) for n in self.nodes}
        queue = deque([n for n in in_degree if in_degree[n] == 0])
        topo_order = []

        while queue:
            source = queue.popleft()
            topo_order.append(source)

            for target in self.graph[source]:
                in_degree[target] -= 1
                if in_degree[target] == 0:
                    queue.append(target)

        return topo_order
