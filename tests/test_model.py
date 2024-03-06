import networkx as nx
import numpy as np
import pytest

from hari_plotter import HariGraph, Model, ModelFactory, Simulation


class TestModel:

    @classmethod
    def setup_class(cls):
        cls.degroot = ModelFactory.from_toml('tests/degroot.toml')
        cls.activity = ModelFactory.from_toml('tests/activity.toml')

    def test_from_toml(self):
        assert isinstance(self.degroot, Model)
        assert isinstance(self.activity, Model)

    def test_init(self):
        model = ModelFactory.create_model("DeGroot", {'gamma': 1})
        assert isinstance(model, Model)

    # def test_get_tension(self):
    #     G = HariGraph.read_network(
    #         'tests/network.txt', 'tests/opinions_0.txt')
    #     assert self.degroot.get_tension(G) == pytest.approx(1.1616793900326015)
