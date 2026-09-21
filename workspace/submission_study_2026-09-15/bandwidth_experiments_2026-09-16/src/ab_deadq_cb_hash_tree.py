"""The same CB/DeadQ placements with payload-free authenticated replacement."""
from ab_deadq_cb_tree import RoutedCBTree
from ab_deadq_cb_hash_level import replace_provisioned


class HashRoutedCBTree(RoutedCBTree):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for d in list(self.levels):
            self.levels[d],self._initial_transports[d]=replace_provisioned(self.levels[d],self._initial_transports[d])
