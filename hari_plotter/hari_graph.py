import json
import math
import os
import random
from itertools import combinations, permutations

import matplotlib.cm as cm
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np


class HariGraph(nx.DiGraph):
    """
    HariGraph extends the DiGraph class of Networkx to offer additional functionality.
    It ensures that each node has a label and provides methods to create, save, and load graphs.
    """

    def __init__(self, incoming_graph_data=None, **attr):
        super().__init__(incoming_graph_data, **attr)
        self.generate_labels()
        self.similarity_function = self.default_similarity_function

    def generate_labels(self):
        """Generates labels for the nodes if they don't exist."""
        if not self.nodes:
            return
        if 'label' not in self.nodes[next(iter(self.nodes))]:
            for i in self.nodes:
                self.nodes[i]['label'] = [i]

    def generate_min_max_values(self):
        """
        Generates min_value and max_value for each node in the graph.

        For single nodes, min_value and max_value are equal to the node's value.
        For cluster nodes, min_value is the minimum of the values of the original nodes,
        and max_value is the maximum of the values of the original nodes.
        """
        for node, data in self.nodes(data=True):
            # If the node is a single node, set min_value and max_value to its value
            if 'label' not in data:
                data['min_value'] = data['max_value'] = data['value']

    def remove_self_loops(self):
        """
        Removes any self-loops present in the graph.

        A self-loop is an edge that connects a node to itself.
        """
        # Iterate over all nodes in the graph
        for node in self.nodes:
            # Check if there is an edge from the node to itself and remove it
            if self.has_edge(node, node):
                self.remove_edge(node, node)

    @classmethod
    def read_network(cls, network_file, opinion_file):
        """
        Class method to create an instance of HariGraph from the provided files.

        Parameters:
            network_file (str): The path to the network file.
            opinion_file (str): The path to the opinion file.

        Returns:
            HariGraph: An instance of HariGraph.
        """
        # Create an instance of HariGraph
        G = cls()

        # Read network file and add nodes and edges to the graph
        with open(network_file, 'r') as f:
            next(f)  # Skip header line
            for line in f:
                parts = line.split()
                idx_agent = int(parts[0])
                n_neighbours = int(parts[1])
                indices_neighbours = map(int, parts[2:2+n_neighbours])
                weights = map(float, parts[2+n_neighbours:])

                # Add nodes with initial value 0, value will be updated from opinion_file
                G.add_node(idx_agent, value=0)

                # Add edges with weights
                for neighbour, weight in zip(indices_neighbours, weights):
                    G.add_edge(neighbour, idx_agent, value=weight)

        # Read opinion file and update node values in the G
        with open(opinion_file, 'r') as f:
            next(f)  # Skip header line
            for line in f:
                parts = line.split()
                idx_agent = int(parts[0])
                opinion = float(parts[1])

                # Update node value
                G.nodes[idx_agent]['value'] = opinion

        G.generate_labels()
        G.generate_min_max_values()
        G.remove_self_loops()

        return G

    def write_network(self, network_file, opinion_file):
        '''
        Save the network structure and node opinions to separate files.
        Attention! This save loses the information about the labels.

        :param network_file: The name of the file to write the network structure to.
        :param opinion_file: The name of the file to write the node opinions to.
        '''
        # Save network structure
        with open(network_file, 'w') as f:
            # Write header
            f.write(
                "# idx_agent n_neighbours_in indices_neighbours_in[...] weights_in[...]\n")
            for node in self.nodes:
                # Get incoming neighbors
                neighbors = list(self.predecessors(node))
                weights = [self[neighbor][node]['value']
                           for neighbor in neighbors]  # Get weights of incoming edges
                # Write each node's information in a separate line
                f.write(
                    f"{node} {len(neighbors)} {' '.join(map(str, neighbors + weights))}\n")

        # Save node opinions
        with open(opinion_file, 'w') as f:
            # Write header
            f.write("# idx_agent opinion[...]\n")
            for node, data in self.nodes(data=True):
                # Write each node's opinion value in a separate line
                f.write(f"{node} {data['value']}\n")

    @classmethod
    def read_json(cls, filename):
        """
        Reads a HariGraph from a JSON file.

        :param filename: The name of the file to read from.
        :return: A new HariGraph instance.
        """
        if not os.path.exists(filename):
            raise FileNotFoundError(f"{filename} does not exist.")

        with open(filename, 'r') as file:
            graph_dict = json.load(file)

        G = cls()
        for node in graph_dict["nodes"]:
            G.add_node(node["id"], value=node["value"],
                       # defaulting to value if not present
                       min_value=node.get('min_value', node["value"]),
                       # defaulting to value if not present
                       max_value=node.get('max_value', node["value"]),
                       label=node.get('label', [node["id"]]))

        for edge in graph_dict["edges"]:
            G.add_edge(edge["source"], edge["target"], value=edge["value"])

        return G

    def write_json(self, filename):
        """
        Saves the HariGraph to a JSON file.

        :param filename: The name of the file to write to.
        """
        graph_dict = {
            "nodes": [
                {"id": n,
                 "value": self.nodes[n]["value"],
                 "min_value": self.nodes[n].get('min_value', self.nodes[n]["value"]),
                 "max_value": self.nodes[n].get('max_value', self.nodes[n]["value"]),
                 "label": self.nodes[n].get('label', [n])}
                for n in self.nodes()
            ],
            "edges": [{"source": u, "target": v, "value": self[u][v]["value"]} for u, v in self.edges()]
        }
        with open(filename, 'w') as file:
            json.dump(graph_dict, file)

    @classmethod
    def guaranteed_connected(cls, n):
        """
        Creates a guaranteed connected HariGraph instance with n nodes.

        :param n: Number of nodes.
        :return: A new HariGraph instance.
        """
        if n < 2:
            raise ValueError("Number of nodes should be at least 2")

        G = cls()
        for i in range(n):
            G.add_node(i, value=random.random())

        nodes = list(G.nodes)
        random.shuffle(nodes)
        for i in range(n - 1):
            G.add_edge(nodes[i], nodes[i + 1], value=random.random())

        additional_edges = random.randint(1, n)
        for _ in range(additional_edges):
            u, v = random.sample(G.nodes, 2)
            if u != v and not G.has_edge(u, v):
                G.add_edge(u, v, value=random.random())
                if random.choice([True, False]) and not G.has_edge(v, u):
                    G.add_edge(v, u, value=random.random())

        G.generate_labels()
        G.generate_min_max_values()

        return G

    @classmethod
    def by_deletion(cls, n, factor):
        """
        Creates a HariGraph instance by deleting some of the edges of a fully connected graph.

        :param n: Number of nodes.
        :param factor: Factor representing how many edges to keep.
        :return: A new HariGraph instance.
        """
        if not 0 <= 1 - factor <= 1:
            raise ValueError("Deletion factor must be between 0 and 1")
        if n < 2:
            raise ValueError("Number of nodes should be at least 2")

        G = cls()
        for i in range(n):
            G.add_node(i, value=random.random())
        for i in range(n):
            for j in range(n):
                if i != j:
                    G.add_edge(i, j, value=random.random())

        edges_to_remove = random.sample(
            G.edges, int(len(G.edges) * (1 - factor)))
        G.remove_edges_from(edges_to_remove)

        G.generate_labels()
        G.generate_min_max_values()

        return G

    @classmethod
    def strongly_connected_components(cls, n1, n2, connect_nodes=2):
        """
        Creates a HariGraph instance with two strongly connected components, 
        one with a value close to 1 and the other close to 0.

        :param n1: Number of nodes in the first component.
        :param n2: Number of nodes in the second component.
        :param connect_nodes: Number of nodes to connect between components, ensuring weak connectivity.
        :return: A new HariGraph instance.
        """
        if n1 < 2 or n2 < 2:
            raise ValueError(
                "Number of nodes in each component should be at least 2")

        if connect_nodes < 2:
            raise ValueError("Number of connecting nodes should be at least 2")

        if connect_nodes > min(n1, n2):
            raise ValueError(
                "Number of connecting nodes should not exceed the number of nodes in any component")

        G = cls()

        # Create the first strongly connected component with values close to 1
        for i in range(n1):
            G.add_node(i, value=0.9 + random.uniform(0, 0.1))
        for i in range(n1):
            for j in range(i + 1, n1):
                G.add_edge(i, j, value=random.random())
                G.add_edge(j, i, value=random.random())

        # Create the second strongly connected component with values close to 0
        for i in range(n1, n1 + n2):
            G.add_node(i, value=random.uniform(0, 0.1))
        for i in range(n1, n1 + n2):
            for j in range(i + 1, n1 + n2):
                G.add_edge(i, j, value=random.random())
                G.add_edge(j, i, value=random.random())

        # Connect the components weakly
        first_component_nodes = list(range(n1))
        second_component_nodes = list(range(n1, n1 + n2))

        # Splitting connect_nodes randomly into two parts, each at least 1.
        split = random.randint(1, connect_nodes - 1)
        connect_nodes_first_to_second = split
        connect_nodes_second_to_first = connect_nodes - split

        # Creating connections from the first component to the second
        for _ in range(connect_nodes_first_to_second):
            u = random.choice(first_component_nodes)
            v = random.choice(second_component_nodes)
            while G.has_edge(u, v):
                u = random.choice(first_component_nodes)
                v = random.choice(second_component_nodes)
            G.add_edge(u, v, value=random.random())

        # Creating connections from the second component to the first
        for _ in range(connect_nodes_second_to_first):
            u = random.choice(second_component_nodes)
            v = random.choice(first_component_nodes)
            while G.has_edge(u, v):
                u = random.choice(second_component_nodes)
                v = random.choice(first_component_nodes)
            G.add_edge(u, v, value=random.random())

        G.generate_labels()
        G.generate_min_max_values()

        return G

    def copy(self):
        G_copy = super().copy(as_view=False)
        G_copy = HariGraph(G_copy) if not isinstance(
            G_copy, HariGraph) else G_copy
        G_copy.similarity_function = self.similarity_function
        return G_copy

    def check_all_paths_exist(self):
        """
        Checks if there exists a path between every pair of nodes in the HariGraph instance.

        :return: True if a path exists between every pair of nodes, False otherwise.
        """
        for source, target in permutations(self.nodes, 2):
            if not nx.has_path(self, source, target):
                # print(f"No path exists from {source} to {target}")
                return False
        return True

    def dynamics_step(self, t):
        """
        Updates the value of each node in the HariGraph instance based on the values of its predecessors.

        :param t: The time step factor influencing the dynamics.
        """
        updated_values = {}  # Temporary dictionary to store updated values

        for i in self.nodes:
            vi = self.nodes[i]['value']

            # Predecessors of a node are the start nodes of its incoming edges.
            for j in self.predecessors(i):
                pij = self[j][i]['value']
                vj = self.nodes[j]['value']
                vi += pij * vj * t  # Calculate updated value based on each incoming edge

            # Clip the updated value to [0, 1]
            vi = max(0, min(vi, 1))

            updated_values[i] = vi

        # Update the values in the graph with the calculated updated values
        for i, vi in updated_values.items():
            self.nodes[i]['value'] = vi

    @property
    def weighted_mean_value(self):
        """
        Calculates the weighted mean value of the nodes in the graph.

        For each node, its value is multiplied by its weight. 
        The weight of a node is the length of its label if defined, 
        otherwise, it is assumed to be 1. The method returns the 
        sum of the weighted values divided by the sum of the weights.

        Returns:
            float: The weighted mean value of the nodes in the graph. 
                Returns 0 if the total weight is 0 to avoid division by zero.
        """
        total_value = 0
        total_weight = 0

        for node in self.nodes:
            value = self.nodes[node]['value']

            # If label is defined, the weight is the length of the label.
            # If not defined, the weight is assumed to be 1.
            weight = len(self.nodes[node].get('label', [node]))

            total_value += value * weight
            total_weight += weight

        if total_weight == 0:  # Prevent division by zero
            return 0

        return total_value / total_weight

    @staticmethod
    def default_similarity_function(vi, vj, size_i, size_j, edge_value, reverse_edge_value,
                                    value_coef=1., extreme_coef=0.1, influence_coef=1., size_coef=10.):
        """
        The default function used to calculate the similarity between two nodes.

        Parameters:
            vi (float): The value attribute of node i.
            vj (float): The value attribute of node j.
            size_i (int): The length of the label of node i.
            size_j (int): The length of the label of node j.
            edge_value (float): The value attribute of the edge from node i to node j, if it exists, else None.
            reverse_edge_value (float): The value attribute of the edge from node j to node i, if it exists, else None.
            value_coef (float): Coefficient for value proximity impact.
            extreme_coef (float): Coefficient for extreme proximity impact.
            influence_coef (float): Coefficient for influence impact.
            size_coef (float): Coefficient for size impact.

        Returns:
            float: The computed similarity value between node i and node j.
        """
        # Calculate Value Proximity Impact (high if values are close)
        value_proximity = value_coef * (1 - abs(vi - vj))

        # Calculate Proximity to 0 or 1 Impact (high if values are close to 0 or 1)
        extreme_proximity = extreme_coef * \
            min(min(vi, vj), min(1 - vi, 1 - vj))

        # Calculate Influence Impact (high if influence is high)
        influence = 0
        label_sum = size_i + size_j

        if edge_value is not None:  # if an edge exists between the nodes
            influence += (edge_value * size_j) / label_sum

        if reverse_edge_value is not None:  # if a reverse edge exists between the nodes
            influence += (reverse_edge_value * size_i) / label_sum

        influence *= influence_coef  # Apply Influence Coefficient

        # Calculate Size Impact (high if size is low)
        size_impact = size_coef * \
            (1 / (1 + size_i) + 1 / (1 + size_j))

        # Combine the impacts
        return value_proximity + extreme_proximity + influence + size_impact

    def compute_similarity(self, i, j, similarity_function=None):
        """
        Computes the similarity between two nodes in the graph.

        Parameters:
            i (int): The identifier for the first node.
            j (int): The identifier for the second node.
            similarity_function (callable, optional): 
                A custom similarity function to be used for this computation. 
                If None, the instance's similarity_function is used. 
                Default is None.

        Returns:
            float: The computed similarity value between nodes i and j.
        """
        # Check if there is an edge between nodes i and j
        if not self.has_edge(i, j) and not self.has_edge(j, i):
            return -2

        # Extract parameters from node i, node j, and the edge (if exists)
        vi = self.nodes[i]['value']
        vj = self.nodes[j]['value']

        size_i = len(self.nodes[i].get('label', [i]))
        size_j = len(self.nodes[j].get('label', [j]))

        edge_value = self[i][j]['value'] if self.has_edge(i, j) else None
        reverse_edge_value = self[j][i]['value'] if self.has_edge(
            j, i) else None

        # Choose the correct similarity function and calculate the similarity
        func = similarity_function or self.similarity_function
        return func(vi, vj, size_i, size_j, edge_value, reverse_edge_value)

    def merge_nodes(self, i, j):
        """
        Merges two nodes in the graph into a new node.

        The new node's value is a weighted average of the values of 
        the merged nodes, and its label is the concatenation of the labels 
        of the merged nodes. The edges are reconnected to the new node, 
        and the old nodes are removed.

        Parameters:
            i (int): The identifier for the first node to merge.
            j (int): The identifier for the second node to merge.
        """
        # Calculate new value, label, min_value, and max_value
        label_i = self.nodes[i].get('label', [i])
        label_j = self.nodes[j].get('label', [j])
        new_label = label_i + label_j

        vi = self.nodes[i]['value']
        vj = self.nodes[j]['value']

        min_value = min(self.nodes[i].get(
            'min_value', vi), self.nodes[j].get('min_value', vj))
        max_value = max(self.nodes[i].get(
            'max_value', vi), self.nodes[j].get('max_value', vj))

        weight_i = len(label_i)
        weight_j = len(label_j)
        new_value = (vi * weight_i + vj * weight_j) / (weight_i + weight_j)

        # Add a new node to the graph with the calculated value, label, min_value, and max_value
        new_node = max(self.nodes) + 1
        self.add_node(new_node, value=new_value, label=new_label,
                      min_value=min_value, max_value=max_value)

        # Reconnect edges
        for u, v, data in list(self.edges(data=True)):
            if u == i or u == j:
                if v != i and v != j:  # Avoid connecting the new node to itself
                    value = self[u][v]['value']
                    if self.has_edge(new_node, v):
                        # Sum the values if both original nodes were connected to the same node
                        self[new_node][v]['value'] += value
                    else:
                        self.add_edge(new_node, v, value=value)
                if self.has_edge(u, v):  # Check if the edge exists before removing it
                    self.remove_edge(u, v)
            if v == i or v == j:
                if u != i and u != j:  # Avoid connecting the new node to itself
                    value = self[u][v]['value']
                    if self.has_edge(u, new_node):
                        # Sum the values if both original nodes were connected to the same node
                        self[u][new_node]['value'] += value
                    else:
                        self.add_edge(u, new_node, value=value)
                if self.has_edge(u, v):  # Check if the edge exists before removing it
                    self.remove_edge(u, v)

        # Remove the old nodes
        self.remove_node(i)
        self.remove_node(j)

    def find_clusters(self, max_opinion_difference=0.1, min_influence=0.1):
        """
        Finds clusters of nodes in the graph where the difference in the nodes' values 
        is less than max_opinion_difference, and the influence of i on j is higher than 
        min_influence * size(i).

        Parameters:
            max_opinion_difference (float): Maximum allowed difference in the values of nodes to form a cluster.
            min_influence (float): Minimum required influence to form a cluster, adjusted by the size of the node.

        Returns:
            List[List[int]]: A list of lists, where each inner list represents a cluster of node identifiers.
        """
        clusters = []
        visited_nodes = set()

        for i in self.nodes:
            if i in visited_nodes:
                continue

            cluster = [i]
            visited_nodes.add(i)

            # Use a list as a simple queue for Breadth-First Search (BFS)
            queue = [i]

            while queue:
                node = queue.pop(0)  # Dequeue a node

                for neighbor in set(self.successors(node)).union(self.predecessors(node)):
                    if neighbor in visited_nodes:
                        continue  # Skip already visited nodes

                    vi = self.nodes[node]['value']
                    vj = self.nodes[neighbor]['value']
                    size_i = len(self.nodes[node].get('label', [node]))

                    if self.has_edge(node, neighbor):
                        influence_ij = self[node][neighbor]['value']
                    else:
                        influence_ij = 0

                    if self.has_edge(neighbor, node):
                        influence_ji = self[neighbor][node]['value']
                    else:
                        influence_ji = 0

                    # Check conditions for being in the same cluster
                    if (abs(vi - vj) <= max_opinion_difference and
                            (influence_ij >= min_influence * size_i or
                             influence_ji >= min_influence * size_i)):
                        cluster.append(neighbor)  # Add to the current cluster
                        visited_nodes.add(neighbor)
                        queue.append(neighbor)  # Enqueue for BFS

            # Add found cluster to the list of clusters
            clusters.append(cluster)

        return clusters

    def merge_by_intervals(self, intervals):
        """
        Merges nodes into clusters based on the intervals defined by the input list of values.

        Parameters:
            intervals (List[float]): A sorted list of values between 0 and 1 representing the boundaries of the intervals.
        """
        if not all(0 <= val <= 1 for val in intervals):
            raise ValueError("All values in intervals must be between 0 and 1")
        if not intervals:
            raise ValueError("Intervals list cannot be empty")

        # Sort the intervals to ensure they are in ascending order
        intervals = sorted(intervals)

        # Create a list to hold the clusters
        clusters = [[] for _ in range(len(intervals) + 1)]

        # Define the intervals
        intervals = [0] + intervals + [1]
        for i in range(len(intervals) - 1):
            lower_bound = intervals[i]
            upper_bound = intervals[i + 1]

            # Iterate over all nodes and assign them to the appropriate cluster
            for node, data in self.nodes(data=True):
                value = data.get('value', 0)
                if lower_bound <= value < upper_bound:
                    clusters[i].append(node)

        # Convert the clusters list of lists to a list of sets
        clusters = [set(cluster) for cluster in clusters if cluster]

        # Merge the clusters
        if clusters:
            self.merge_clusters(clusters)

    def get_cluster_mapping(self):
        """
        Generates a mapping of current clusters in the graph.

        The method returns a dictionary where the key is the ID of a current node
        and the value is a set containing the IDs of the original nodes that were merged 
        to form that node.

        :return: A dictionary representing the current clusters in the graph.
        """
        cluster_mapping = {}
        for node in self.nodes:
            label = self.nodes[node].get('label', [node])
            cluster_mapping[node] = set(label)
        return cluster_mapping

    def merge_clusters(self, clusters):
        """
        Merges clusters of nodes in the graph into new nodes.

        For each cluster, a new node is created whose value is the weighted 
        average of the values of the nodes in the cluster, with the weights 
        being the lengths of the labels of the nodes. The new node's label 
        is the concatenation of the labels of the nodes in the cluster.
        The edges are reconnected to the new nodes, and the old nodes are removed.

        Parameters:
            clusters (Union[List[Set[int]], Dict[int, int]]): A list where each element is a set containing 
                                    the IDs of the nodes in a cluster to be merged or a dictionary mapping old node IDs
                                    to new node IDs.
        """

        # Determine whether clusters are provided as a list or a dictionary
        if isinstance(clusters, dict):
            # Create id_mapping dictionary where each old node ID is mapped to its new node ID
            id_mapping = {}
            for new_id, old_ids_set in clusters.items():
                for old_id in old_ids_set:
                    id_mapping[old_id] = new_id
            new_ids = set(id_mapping.values())
            clusters_list = [set(old_id for old_id, mapped_id in id_mapping.items(
            ) if mapped_id == new_id) for new_id in new_ids]
        elif isinstance(clusters, list):
            id_mapping = {}
            # Define clusters_list here when clusters is a list.
            clusters_list = clusters
            new_id_start = max(self.nodes) + 1
            for i, cluster in enumerate(clusters):
                new_id = new_id_start + i
                for node_id in cluster:
                    assert node_id in self.nodes and node_id not in id_mapping, f"Node {node_id} already exists in the graph or is being merged multiple times."
                    id_mapping[node_id] = new_id
        else:
            raise ValueError(
                "clusters must be a list of sets or a dictionary.")

        # Creating New Nodes with combined labels, importances, and values.
        for i, cluster in enumerate(clusters_list):
            new_id = id_mapping[next(iter(cluster))]
            labels = []
            importance = 0
            total_value = 0
            total_weight = 0
            min_value = float('inf')
            max_value = float('-inf')

            for node_id in cluster:
                node = self.nodes[node_id]
                labels.extend(node.get('label', [node_id]))
                importance += node.get('importance', 0)
                value = node.get('value', 0)
                min_value = min(min_value, node.get('min_value', value))
                max_value = max(max_value, node.get('max_value', value))
                weight = len(node.get('label', [node_id]))
                total_value += value * weight
                total_weight += weight

            new_value = total_value / total_weight if total_weight > 0 else 0
            self.add_node(new_id, label=labels, importance=importance,
                          value=new_value, min_value=min_value, max_value=max_value)

        # Reassigning Edges to New Nodes and Removing Old Nodes.
        for old_node_id, new_id in id_mapping.items():
            for successor in self.successors(old_node_id):
                mapped_successor = id_mapping.get(successor, successor)
                if mapped_successor != new_id:  # avoid creating self-loop
                    self.add_edge(new_id, mapped_successor,
                                  value=self[old_node_id][successor]['value'])

            for predecessor in self.predecessors(old_node_id):
                mapped_predecessor = id_mapping.get(predecessor, predecessor)
                if mapped_predecessor != new_id:  # avoid creating self-loop
                    self.add_edge(mapped_predecessor, new_id,
                                  value=self[predecessor][old_node_id]['value'])

            self.remove_node(old_node_id)

    def simplify_graph_one_iteration(self):
        """
        Simplifies the graph by one iteration.

        In each iteration, it finds the pair of nodes with the maximum similarity 
        and merges them. If labels are not initialized, it initializes them. 
        If there is only one node left, no further simplification is possible.

        Returns:
            HariGraph: The simplified graph.
        """
        # Check if labels are initialized, if not, initialize them
        if 'label' not in self.nodes[next(iter(self.nodes))]:
            for i in self.nodes:
                self.nodes[i]['label'] = [i]

        # If there is only one node left, no further simplification is possible
        if self.number_of_nodes() <= 1:
            return self

        # Find the pair of nodes with the maximum similarity
        max_similarity = -1
        pair = None
        for i, j in combinations(self.nodes, 2):
            similarity = self.compute_similarity(i, j)
            if similarity > max_similarity:
                max_similarity = similarity
                pair = (i, j)

        # Merge the nodes with the maximum similarity
        if pair:
            i, j = pair
            self = self.merge_nodes(i, j)

    def position_nodes(self, seed=None):
        """
        Determines the positions of the nodes in the graph using the spring layout algorithm.

        :param seed: int, optional
            Seed for the spring layout algorithm, affecting the randomness in the positioning of the nodes.
            If None, the positioning of the nodes will be determined by the underlying algorithm's default behavior.
            Default is None.

        :return: dict
            A dictionary representing the positions of the nodes in a 2D space, where the keys are node IDs
            and the values are the corresponding (x, y) coordinates.
        """
        return nx.spring_layout(self, seed=seed)

    def draw(self, pos=None, plot_node_info='none', use_node_color=True,
             use_edge_thickness=True, plot_edge_values=False,
             node_size_multiplier=200,
             arrowhead_length=0.2, arrowhead_width=0.2,
             min_line_width=0.1, max_line_width=3.0,
             seed=None, save_filepath=None, show=True,
             fig=None, ax=None, bottom_right_text=None):
        """
        Visualizes the graph with various customization options.

        :param pos: dict, optional
            Position of nodes as a dictionary of coordinates. If not provided, the spring layout is used to position nodes.

        :param plot_node_info: str, optional
            Determines the information to display on the nodes.
            Options: 'none', 'values', 'ids', 'labels', 'size'. Default is 'none'.

        :param use_node_color: bool, optional
            If True, nodes are colored based on their values using a colormap. Default is True.

        :param use_edge_thickness: bool, optional
            If True, the thickness of the edges is determined by their values, scaled between min_line_width and max_line_width. Default is True.

        :param plot_edge_values: bool, optional
            If True, displays the values of the edges on the plot. Default is False.

        :param node_size_multiplier: int, optional
            Multiplier for node sizes, affecting the visualization scale. Default is 200.

        :param arrowhead_length: float, optional
            Length of the arrowhead for directed edges. Default is 0.2.

        :param arrowhead_width: float, optional
            Width of the arrowhead for directed edges. Default is 0.2.

        :param min_line_width: float, optional
            Minimum line width for edges. Default is 0.1.

        :param max_line_width: float, optional
            Maximum line width for edges. Default is 3.0.

        :param seed: int, optional
            Seed for the spring layout. Affects the randomness in the positioning of the nodes. Default is None.

        :param save_filepath: str, optional
            If provided, saves the plot to the specified filepath. Default is None.

        :param show: bool, optional
            If True, displays the plot immediately. Default is True.

        :param fig: matplotlib.figure.Figure, optional
            Matplotlib Figure object. If None, a new figure is created. Default is None.

        :param ax: matplotlib.axes._axes.Axes, optional
            Matplotlib Axes object. If None, a new axis is created. Default is None.

        :param bottom_right_text: str, optional
            Text to display in the bottom right corner of the plot. Default is None.

        :return: tuple
            A tuple containing the Matplotlib Figure and Axes objects.
        """
        if fig is None or ax is None:
            fig, ax = plt.subplots(figsize=(10, 7))

        if pos is None:
            pos = self.position_nodes(seed=seed)

        # Get the node and edge attributes
        node_attributes = nx.get_node_attributes(self, 'value')
        edge_attributes = nx.get_edge_attributes(self, 'value')

        # Prepare Node Labels
        node_labels = {}
        if plot_node_info == 'values':
            node_labels = {node: f"{value:.2f}" for node,
                           value in node_attributes.items()}
        elif plot_node_info == 'ids':
            node_labels = {node: f"{node}" for node in self.nodes}
        elif plot_node_info == 'labels':
            for node in self.nodes:
                label = self.nodes[node].get('label', None)
                if label is not None:
                    node_labels[node] = ','.join(map(str, label))
                else:  # If label is not defined, show id instead
                    node_labels[node] = str(node)
        elif plot_node_info == 'size':
            for node in self.nodes:
                label_len = len(self.nodes[node].get('label', [node]))
                node_labels[node] = str(label_len)

        # Prepare Node Colors
        if use_node_color:
            node_colors = [cm.bwr(value) for value in node_attributes.values()]
        else:
            node_colors = 'lightblue'

        # Prepare Edge Widths
        if use_edge_thickness:

            # Gather edge weights
            edge_weights = list(edge_attributes.values())

            # Scale edge weights non-linearly
            # or np.log1p(edge_weights) for logarithmic scaling
            scaled_weights = np.sqrt(edge_weights)

            # Normalize scaled weights to range [min_line_width, max_line_width]
            max_scaled_weight = max(scaled_weights)
            min_scaled_weight = min(scaled_weights)

            edge_widths = [
                min_line_width + (max_line_width - min_line_width) * (weight -
                                                                      min_scaled_weight) / (max_scaled_weight - min_scaled_weight)
                for weight in scaled_weights
            ]

        else:
            # Default line width applied to all edges
            edge_widths = [1.0] * self.number_of_edges()

        # Prepare Edge Labels
        edge_labels = None
        if plot_edge_values:
            edge_labels = {(u, v): f"{value:.2f}" for (u, v),
                           value in edge_attributes.items()}

        # Calculate Node Sizes
        node_sizes = []
        for node in self.nodes:
            label_len = len(self.nodes[node].get('label', [node]))
            size = node_size_multiplier * \
                math.sqrt(label_len)  # Nonlinear scaling
            node_sizes.append(size)

        # Draw Nodes and Edges
        nx.draw_networkx_nodes(
            self, pos, node_color=node_colors, node_size=node_sizes, ax=ax)

        for (u, v), width in zip(self.edges(), edge_widths):
            # Here, node_v_size and node_u_size represent the sizes (or the "radii") of the nodes.
            node_v_size = node_sizes[list(self.nodes).index(v)]
            node_u_size = node_sizes[list(self.nodes).index(u)]

            # Adjust the margins based on node sizes to avoid collision with arrowheads and to avoid unnecessary gaps.
            target_margin = 5*node_v_size / node_size_multiplier
            source_margin = 5*node_u_size / node_size_multiplier

            if self.has_edge(v, u):
                nx.draw_networkx_edges(self, pos, edgelist=[(u, v)], width=width, connectionstyle='arc3,rad=0.3',
                                       arrowstyle=f'->,head_length={arrowhead_length},head_width={arrowhead_width}', min_target_margin=target_margin, min_source_margin=source_margin)
            else:
                nx.draw_networkx_edges(self, pos, edgelist=[(
                    u, v)], width=width, arrowstyle=f'-|>,head_length={arrowhead_length},head_width={arrowhead_width}', min_target_margin=target_margin, min_source_margin=source_margin)

        # Draw Labels
        nx.draw_networkx_labels(self, pos, labels=node_labels)
        if edge_labels:
            nx.draw_networkx_edge_labels(self, pos, edge_labels=edge_labels)

        # Add text in the bottom right corner if provided
        if bottom_right_text:
            ax.text(1, 0, bottom_right_text, horizontalalignment='right',
                    verticalalignment='bottom', transform=ax.transAxes)

        # Save the plot if save_filepath is provided
        if save_filepath:
            plt.savefig(save_filepath)

        # Show the plot if show is True
        if show:
            plt.show()
        return fig, ax

    @property
    def cluster_size(self):
        """
        Returns a dictionary with the sizes of the nodes.
        Key is the node ID, and value is the size of the node.
        """
        return {node: len(self.nodes[node].get('label', [node])) for node in self.nodes}

    @property
    def importance(self):
        """
        Returns a dictionary with the importance of the nodes.
        Key is the node ID, and value is the ratio of the sum of influences of the node to the size of the node.
        """
        importance_dict = {}
        size_dict = self.cluster_size

        for node in self.nodes:
            influences_sum = sum(data['value']
                                 for _, _, data in self.edges(node, data=True))
            importance_dict[node] = influences_sum / \
                size_dict[node] if size_dict[node] != 0 else 0

        return importance_dict

    @property
    def values(self):
        """
        Returns a dictionary with the values of the nodes.
        Key is the node ID, and value is the value of the node.
        """
        return {node: self.nodes[node]["value"] for node in self.nodes}

    @property
    def min_values(self):
        """
        Returns a dictionary with the minimum values of the nodes.
        Key is the node ID, and value is the min_value of the node.
        """
        return {node: self.nodes[node].get('min_value', self.nodes[node]["value"]) for node in self.nodes}

    @property
    def max_values(self):
        """
        Returns a dictionary with the maximum values of the nodes.
        Key is the node ID, and value is the max_value of the node.
        """
        return {node: self.nodes[node].get('max_value', self.nodes[node]["value"]) for node in self.nodes}

    def __str__(self):
        return f"<HariGraph with {self.number_of_nodes()} nodes and {self.number_of_edges()} edges>"

    def __repr__(self):
        return f"<HariGraph object at {id(self)}: {self.number_of_nodes()} nodes, {self.number_of_edges()} edges>"
