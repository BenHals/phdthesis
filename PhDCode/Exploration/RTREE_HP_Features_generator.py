import numpy as np
import math
from array import array
from skmultiflow.data.base_stream import Stream
from skmultiflow.utils import check_random_state

from scipy.stats import norm, skewnorm
from scipy.special import expit

def generate_narrow_norm_inter(ci, rs):
    return rs.normal(52, 0.01) if ci else rs.normal(48, 0.01)
def generate_wide_norm_inter(ci, rs):
    return rs.normal(50, 10)
def generate_binom_inter(ci, rs):
    return rs.normal(0, 1) if ci else rs.normal(100, 1)

def generate_f1(mu, ci, rs):
    return rs.normal(mu, 50)

def generate_f2(mu, ci, rs):
    return rs.normal(mu, 1)

def generate_f3(mu, ci, rs):
    return rs.normal(mu, 1)

def generate_f4(mu, ci, rs):
    skew = 500 if ci else -500
    rv = skewnorm(loc=mu, scale=25, a=skew)
    rv.random_state = rs

    v = rv.rvs(random_state = rs)
    while v < 0 or v > 100:
        v = rv.rvs(random_state = rs)
    return v

def sinh_archsinh_transformation(x,epsilon,delta):
    return norm.pdf(np.sinh(delta*np.arcsinh(x)-epsilon))*delta*np.cosh(delta*np.arcsinh(x)-epsilon)/np.sqrt(1+np.power(x,2))

def mean_stdev_skew_kurt_sample(rand_state, mean, stdev, skew, kurtosis):
    Z = rand_state.normal(loc = 0, scale = 1)
    X = np.sinh((1/kurtosis)*(np.arcsinh(Z) + skew))
    return ((mean / stdev) + X) * stdev


def concept_gen_distribution(rs, gen_mean, gen_stdev, gen_skew, gen_kurtosis):
    return mean_stdev_skew_kurt_sample(rs, gen_mean, gen_stdev, gen_skew, gen_kurtosis)

def concept_normal(rs, im, isd, isk, ik):
    return rs.normal(loc=50, scale=50)

def concept_binormal(rs, im, isd, isk, ik):
    select = rs.rand()
    return rs.normal(loc=0, scale=1) if select < 0.5 else rs.normal(loc=100, scale=1)

def concept_uniform(rs, im, isd, isk, ik):
    return rs.rand()

class Sampler():
    def __init__(self, num_features, random_state = None, inter_concept_dist='uniform', intra_concept_dist='uniform', features = ['f1', 'f2', 'f3', 'f4'], strength = 1):
        self.num_features = num_features
        self.random_state = check_random_state(random_state)
        self.features = features
        self.strength = strength
        self.feature_data = []
        self.concept_rand_dist = None
        self.inter_concept_dist = inter_concept_dist
        self.intra_concept_dist = intra_concept_dist
        self.ci = random_state % 2 == 0
        print(self.intra_concept_dist)
        print(self.inter_concept_dist)
        for i in range(self.num_features):
            data = {}
            if self.features[i] == 'f1':
                data['mean'] = generate_narrow_norm_inter(self.ci, self.random_state)
            if self.features[i] == 'f2':
                data['mean'] = generate_binom_inter(self.ci, self.random_state)
            if self.features[i] == 'f3':
                data['mean'] = generate_wide_norm_inter(self.ci, self.random_state)
            if self.features[i] == 'f4':
                data['mean'] = generate_narrow_norm_inter(self.ci, self.random_state)
            self.feature_data.append(data)

    def get_sample(self, i):
        mu = self.feature_data[i]['mean']
        x = None
        if self.features[i] == 'f1':
            x = generate_f1(mu, self.ci, self.random_state)
        if self.features[i] == 'f2':
            x = generate_f2(mu, self.ci, self.random_state)
        if self.features[i] == 'f3':
            x = generate_f3(mu, self.ci, self.random_state)
        if self.features[i] == 'f4':
            x = generate_f4(mu, self.ci, self.random_state)
        return x



class RandomTreeGeneratorHPFeatureSample(Stream):
    """ Random Tree stream generator.
       
    This generator is built based on its description in Domingo and Hulten's 
    'Knowledge Discovery and Data Mining'. The generator is based on a random 
    tree that splits features at random and sets labels to its leafs.
    
    The tree structure is composed on Node objects, which can be either inner 
    nodes or leaf nodes. The choice comes as a function fo the parameters 
    passed to its initializer.
    
    Since the concepts are generated and classified according to a tree 
    structure, in theory, it should favour decision tree learners.
    
    Parameters
    ----------
    tree_random_state: int (Default: None)
        Seed for random generation of tree.
    
    sample_random_state: int (Default: None)
        Seed for random generation of instances.
    
    n_classes: int (Default: 2)
        The number of classes to generate.
    
    n_cat_features: int (Default: 5)
        The number of categorical features to generate. Categorical features are binary encoded, the actual number of
        categorical features is `n_cat_features`x`n_categories_per_cat_feature`
    
    n_num_features: int (Default: 5)
        The number of numerical features to generate.
    
    n_categories_per_cat_feature: int (Default: 5)
        The number of values to generate per categorical feature.
    
    max_tree_depth: int (Default: 5)
        The maximum depth of the tree concept.
    
    min_leaf_depth: int (Default: 3)
        The first level of the tree above MaxTreeDepth that can have leaves.
    
    fraction_leaves_per_level: float (Default: 0.15)
        The fraction of leaves per level from min_leaf_depth onwards.
        
    Examples
    --------
    >>> # Imports
    >>> from skmultiflow.data.random_tree_generator import RandomTreeGeneratorSample
    >>> # Setting up the stream
    >>> stream = RandomTreeGeneratorSample(tree_random_state=8873, sample_random_seed=69, n_classes=2, n_cat_features=2,
    ... n_num_features=5, n_categories_per_cat_feature=5, max_tree_depth=6, min_leaf_depth=3,
    ... fraction_leaves_per_level=0.15)
    >>> stream.prepare_for_use()
    >>> # Retrieving one sample
    >>> stream.next_sample()
    (array([[ 0.16268102,  0.1105941 ,  0.7172657 ,  0.13021257,  0.61664241,
         1.        ,  0.        ,  0.        ,  0.        ,  0.        ,
         0.        ,  0.        ,  0.        ,  1.        ,  0.        ]]), array([ 0.]))
    >>> # Retrieving 10 samples
    >>> stream.next_sample(10)
    (array([[ 0.23752865,  0.58739728,  0.33649431,  0.62104964,  0.85182531,
         0.        ,  0.        ,  0.        ,  0.        ,  1.        ,
         0.        ,  0.        ,  0.        ,  0.        ,  1.        ],
       [ 0.80996022,  0.71970756,  0.49121675,  0.18175096,  0.41738968,
         0.        ,  0.        ,  0.        ,  1.        ,  0.        ,
         0.        ,  0.        ,  0.        ,  0.        ,  1.        ],
       [ 0.3450778 ,  0.27301117,  0.52986614,  0.68253015,  0.79836113,
         0.        ,  0.        ,  1.        ,  0.        ,  0.        ,
         1.        ,  0.        ,  0.        ,  0.        ,  0.        ],
       [ 0.28974746,  0.64385678,  0.11726876,  0.14956833,  0.90919843,
         0.        ,  1.        ,  0.        ,  0.        ,  0.        ,
         0.        ,  0.        ,  0.        ,  1.        ,  0.        ],
       [ 0.85404693,  0.77693923,  0.25851095,  0.13574941,  0.01739845,
         0.        ,  0.        ,  0.        ,  0.        ,  1.        ,
         0.        ,  0.        ,  0.        ,  0.        ,  1.        ],
       [ 0.23404205,  0.67644455,  0.65199858,  0.22742471,  0.01895565,
         1.        ,  0.        ,  0.        ,  0.        ,  0.        ,
         0.        ,  0.        ,  1.        ,  0.        ,  0.        ],
       [ 0.12843591,  0.56112384,  0.08013747,  0.46674409,  0.48333615,
         0.        ,  0.        ,  1.        ,  0.        ,  0.        ,
         1.        ,  0.        ,  0.        ,  0.        ,  0.        ],
       [ 0.52058342,  0.51999097,  0.28294293,  0.11435212,  0.83731519,
         0.        ,  1.        ,  0.        ,  0.        ,  0.        ,
         1.        ,  0.        ,  0.        ,  0.        ,  0.        ],
       [ 0.82455551,  0.3758063 ,  0.02672009,  0.87081727,  0.3165448 ,
         1.        ,  0.        ,  0.        ,  0.        ,  0.        ,
         0.        ,  0.        ,  0.        ,  1.        ,  0.        ],
       [ 0.03012729,  0.30479727,  0.65407304,  0.14532937,  0.47670874,
         0.        ,  1.        ,  0.        ,  0.        ,  0.        ,
         0.        ,  0.        ,  1.        ,  0.        ,  0.        ]]),
        array([ 1.,  1.,  1.,  1.,  0.,  1.,  1.,  0.,  0.,  0.]))
    >>> # Generators will have infinite remaining instances, so it returns -1
    >>> stream.n_remaining_samples()
    -1
    >>> stream.has_more_samples()
    True
    
    """
    def __init__(self, tree_random_state=None, sample_random_state=None, sampler_random_state=None,
                 sampler_features = None, inter_concept_dist="uniform", intra_concept_dist="dist", strength=1, n_classes=2, n_cat_features=0,
                 n_num_features=4, n_categories_per_cat_feature=5, max_tree_depth=6, min_leaf_depth=4,
                 fraction_leaves_per_level=0.15):
        super().__init__()

        self.tree_random_state = tree_random_state
        self.sample_random_state = sampler_random_state
        self.sampler_random_state = sampler_random_state
        self.sampler_features = sampler_features
        self.strength = strength
        self.n_classes = n_classes
        self.n_targets = 1
        self.n_num_features = min(n_num_features, len(sampler_features))
        self.n_cat_features = n_cat_features
        self.n_categories_per_cat_feature = n_categories_per_cat_feature
        self.n_features = self.n_num_features + self.n_cat_features * self.n_categories_per_cat_feature
        self.max_tree_depth = max_tree_depth
        self.min_leaf_depth = min_leaf_depth
        self.fraction_leaves_per_level = fraction_leaves_per_level
        self.tree_root = None
        self._sample_random_state = None   # This is the actual random_state object used internally
        self.name = "Random Tree Generator"
        self.inter_concept_dist = inter_concept_dist
        self.intra_concept_dist = intra_concept_dist
        self.generate_sampler()

        self.target_names = ["class"]
        self.feature_names = ["att_num_" + str(i) for i in range(self.n_num_features)]
        for i in range(self.n_cat_features):
            for j in range(self.n_categories_per_cat_feature):
                self.feature_names.append("att_nom_" + str(i) + "_val" + str(j))
        self.target_values = [i for i in range(self.n_classes)]

        self._prepare_for_use()

    def get_data(self):
        return self.sampler.feature_data

    def prepare_for_use(self):
        """
        Prepares the stream for use.

        Notes
        -----
        This functions should always be called after the stream initialization.

        """
        self._sample_random_state = check_random_state(self.sample_random_state)
        self.sample_idx = 0

        self.generate_random_tree()
    def _prepare_for_use(self):
        """
        Prepares the stream for use.

        Notes
        -----
        This functions should always be called after the stream initialization.

        """
        self._sample_random_state = check_random_state(self.sample_random_state)
        self.sample_idx = 0

        self.generate_random_tree()

    def generate_sampler(self):
        """ generate_sampler

        Generates a sampling function for drawing values of X.
        Differentiates meta-information between concepts.

        """
        self.sampler = Sampler(self.n_num_features, self.sampler_random_state, intra_concept_dist=self.intra_concept_dist, inter_concept_dist=self.inter_concept_dist, features = self.sampler_features, strength=self.strength)



    def generate_random_tree(self):
        """ generate_random_tree
        
        Generates the random tree, starting from the root node and following 
        the constraints passed as parameters to the initializer. 
        
        The tree is recursively generated, node by node, until it reaches the
        maximum tree depth.
        
        """
        # Starting random generators and parameter arrays
        tree_random_state = check_random_state(self.tree_random_state)
        nominal_att_candidates = array('i')
        min_numeric_value = array('d')
        max_numeric_value = array('d')

        for i in range(self.n_num_features):
            vals = []
            for vi in range(1000):
                vals.append(self.sampler.get_sample(i))
            
            # min_numeric_value.append(0.0)
            # max_numeric_value.append(1.0)
            min_numeric_value.append(min(vals))
            max_numeric_value.append(max(vals))


        for i in range(self.n_num_features + self.n_cat_features):
            nominal_att_candidates.append(i)

        self.tree_root = self.generate_random_tree_node(0, nominal_att_candidates, min_numeric_value, max_numeric_value,
                                                        tree_random_state)

    def generate_random_tree_node(self, current_depth, nominal_att_candidates, min_numeric_value, max_numeric_value,
                                  random_state):
        """ generate_random_tree_node
        
        Creates a node, choosing at random the splitting feature and the
        split value. Fill the features with random feature values, and then 
        recursively generates its children. If the split feature is a
        numerical feature there are going to be two children nodes, one
        for samples where the value for the split feature is smaller than
        the split value, and one for the other case.
        
        Once the recursion passes the leaf minimum depth, it probabilistic 
        chooses if the node is a leaf or not. If not, the recursion follow 
        the same way as before. If it decides the node is a leaf, a class 
        label is chosen for the leaf at random.
        
        Furthermore, if the current_depth is equal or higher than the tree 
        maximum depth, a leaf node is immediately returned.
        
        Parameters
        ----------
        current_depth: int
            The current tree depth.
        
        nominal_att_candidates: array
            A list containing all the, still not chosen for the split, 
            nominal attributes.
        
        min_numeric_value: array
            The minimum value reachable, at this branch of the 
            tree, for all numeric attributes.
        
        max_numeric_value: array
            The minimum value reachable, at this branch of the 
            tree, for all numeric attributes.
            
        random_state: numpy.random
            A numpy random generator instance.
        
        Returns
        -------
        random_tree_generator.Node
            Returns the node, either a inner node or a leaf node.
        
        Notes
        -----
        If the splitting attribute of a node happens to be a nominal attribute 
        we guarantee that none of its children will split on the same attribute, 
        as it would have no use for that split.
         
        """
        if (current_depth >= self.max_tree_depth) or \
                ((current_depth >= self.min_leaf_depth) and
                 (self.fraction_leaves_per_level >= (1.0 - random_state.rand()))):
            leaf = Node()
            leaf.class_label = random_state.randint(0, self.n_classes)
            return leaf

        node = Node()
        chosen_att = random_state.randint(0, len(nominal_att_candidates))
        if chosen_att < self.n_num_features:
            numeric_index = chosen_att
            node.split_att_index = numeric_index
            min_val = min_numeric_value[numeric_index]
            max_val = max_numeric_value[numeric_index]
            node.split_att_value = ((max_val - min_val) * random_state.rand() + min_val)
            # node.split_att_value = ((max_val - min_val) * self.sampler.get_sample(chosen_att) + min_val)
            node.children = []

            new_max_value = max_numeric_value[:]
            new_max_value[numeric_index] = node.split_att_value
            node.children.append(self.generate_random_tree_node(current_depth + 1, nominal_att_candidates,
                                                                min_numeric_value, new_max_value, random_state))

            new_min_value = min_numeric_value[:]
            new_min_value[numeric_index] = node.split_att_value
            node.children.append(self.generate_random_tree_node(current_depth + 1, nominal_att_candidates,
                                                                new_min_value, max_numeric_value, random_state))
        else:
            node.split_att_index = nominal_att_candidates[chosen_att]
            new_nominal_candidates = array('d', nominal_att_candidates)
            new_nominal_candidates.remove(node.split_att_index)

            for i in range(self.n_categories_per_cat_feature):
                node.children.append(self.generate_random_tree_node(current_depth + 1, new_nominal_candidates,
                                                                    min_numeric_value, max_numeric_value, random_state))

        return node

    def classify_instance(self, node, att_values):
        """ classify_instance
        
        After a sample is generated it passes through this function, which 
        advances the tree structure until it finds a leaf node.
        
        Parameters
        ----------
        node: Node object
            The Node that will be verified. Either it's a leaf, and then the 
            label is returned, or it's a inner node, and so the algorithm 
            will continue to advance in the structure.
            
        att_values: numpy.array
            The set of generated feature values of the sample.
        
        Returns
        -------
        tuple or tuple list
            Return a tuple with the features matrix and the labels matrix 
            for the batch_size samples that were requested.
        
        """
        if len(node.children) == 0:
            return node.class_label
        if node.split_att_index < self.n_num_features:
            aux = 0 if att_values[node.split_att_index] < node.split_att_value else 1
            return self.classify_instance(node.children[aux], att_values)
        else:
            return self.classify_instance(
                node.children[self.__get_integer_nominal_attribute_representation(node.split_att_index, att_values)],
                att_values)

    def __get_integer_nominal_attribute_representation(self, nominal_index=None, att_values=None):
        """ __get_integer_nominal_attribute_representation
        
        Utility function, to determine a nominal index when coded in one-hot 
        fashion.
        
        The nominal_index uses as reference the number of nominal attributes 
        plus the number of numerical attributes. 
        
        Parameters
        ----------
        nominal_index: int
            The nominal feature index.
            
        att_values: np.array
            The features array.
            
        Returns
        -------
        int
            This function returns the index of the active variable in a nominal 
            attribute 'hot one' representation.
        
        """
        min_index = self.n_num_features + \
                    (nominal_index - self.n_num_features) * self.n_categories_per_cat_feature
        for i in range(self.n_categories_per_cat_feature):
            if att_values[int(min_index)] == 1:
                return i
            min_index += 1
        return None

    def next_sample(self, batch_size=1):
        """ next_sample
        
        Randomly generates attributes values, and then classify each instance 
        generated.
        
        Parameters
        ----------
        batch_size: int
            The number of samples to return.
         
        Returns
        -------
        tuple or tuple list
            Return a tuple with the features matrix and the labels matrix for the 
            batch_size samples that were requested.
         
        """
        num_attributes = -1
        data = np.zeros([batch_size, self.n_num_features + (self.n_cat_features
                                                            * self.n_categories_per_cat_feature) + 1])
        for j in range(batch_size):
            for i in range(self.n_num_features):
                # A = self._sample_random_state.rand()
                # B = self.sampler.get_sample(i)
                # print(A)
                # print(B)
                # exit()
                # data[j, i] = self._sample_random_state.rand()
                data[j, i] = self.sampler.get_sample(i)

            for i in range(self.n_num_features,
                           self.n_num_features
                           + (self.n_cat_features * self.n_categories_per_cat_feature),
                           self.n_categories_per_cat_feature):
                aux = self._sample_random_state.randint(0, self.n_categories_per_cat_feature)
                for k in range(self.n_categories_per_cat_feature):
                    if aux == k:
                        data[j, k + i] = 1.0
                    else:
                        data[j, k + i] = 0.0

            data[j, self.n_num_features + (self.n_cat_features * self.n_categories_per_cat_feature)] \
                = self.classify_instance(self.tree_root, data[j])

            self.current_sample_x = data[:self.n_num_features + (self.n_cat_features
                                                                 * self.n_categories_per_cat_feature)]

            self.current_sample_y = data[self.n_num_features + (self.n_cat_features
                                                                * self.n_categories_per_cat_feature):]

            num_attributes = self.n_num_features + (self.n_cat_features
                                                    * self.n_categories_per_cat_feature)

        self.current_sample_x = data[:, :num_attributes]
        self.current_sample_y = np.ravel(data[:, num_attributes:])
        return self.current_sample_x, self.current_sample_y


class Node:
    """ Node
    
    Class that stores the attributes of a node. No further methods.
    
    Parameters
    ----------
    class_label: int, optional
        If given it means the node is a leaf and the class label associated 
        with it is class_label.
        
    split_att_index: int, optional
        If given it means the node is an inner node and the split attribute 
        is split_att_index.
        
    split_att_value: int, optional
        If given it means the node is an inner node and the split value is 
        split_att_value.
    
    """
    def __init__(self, class_label=None, split_att_index=None, split_att_value=None):
        self.class_label = class_label
        self.split_att_index = split_att_index
        self.split_att_value = split_att_value
        self.children = []