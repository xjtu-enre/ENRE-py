from neo4j import GraphDatabase

from vis.graphutil import Graph


class Neo4jBuilder:
    def __init__(self, uri, user, password, graph: Graph):
        self.graph = graph
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def print_greeting(self, message):
        with self.driver.session() as session:
            greeting = session.write_transaction(self._create_and_return_greeting, message)
            print(greeting)

    def _create_nodes(self, tx, message):
        for node in self.graph.nodes:
            def create_node(tx, message):
                result = tx.run("CREATE (a: Entity)"
                                "SET a.kind = $kind"
                                "SET a.longname = longname", kind=node.raw_repr["kind"])
        result = tx.run("CREATE ()")

    @staticmethod
    def _create_and_return_greeting(tx, message):
        result = tx.run("CREATE (a:Greeting) "
                        "SET a.message = $message "
                        "RETURN a.message + ', from node ' + id(a)", message=message)
        return result.single()[0]


def build_from_graph(g: Graph):
    greeter = Neo4jBuilder("bolt://localhost:7687", "neo4j", "88888888", g)
    greeter.print_greeting("hello, world")
    greeter.close()
