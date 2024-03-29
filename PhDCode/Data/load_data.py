"""
Load a real world data set with distinguished concepts.
Arrage into a single stream with recurring concepts.
"""
import argparse
import pathlib
import pickle
import csv
import shutil
import math

import pandas as pd
import numpy as np
import json

from skmultiflow.data.file_stream import FileStream
from skmultiflow.data.data_stream import DataStream
from skmultiflow.data.concept_drift_stream import ConceptDriftStream
from skmultiflow.data.stagger_generator import STAGGERGenerator
from skmultiflow.data.agrawal_generator import AGRAWALGenerator
from skmultiflow.data.sea_generator import SEAGenerator
from skmultiflow.data.random_tree_generator import RandomTreeGenerator
from skmultiflow.data.hyper_plane_generator import HyperplaneGenerator
from skmultiflow.data.random_rbf_generator import RandomRBFGenerator
from skmultiflow.data.base_stream import Stream
from skmultiflow.utils import check_random_state
from PhDCode.Data.windsim_generator import WindSimGenerator
from PhDCode.Data.random_tree_sampling_generator import RandomTreeGeneratorSample
from PhDCode.Data.hyper_plane_sampling_generator import HyperplaneSampleGenerator


class AbruptDriftStream(Stream):
    def __init__(self, streams, length, random_state = None, width = None, cat_features_idx=None):
        """ A class to handle concept drift (can handle gradual even with Abrupt in the name!)
        Parameters:
        streams: list
            A list of the stream segments which make up the datastream. Each element should be a 
            tuple containing: (stream start (observation #), stream end (observation #), stream object, stream name (str))
        width: int
            Length of gradual drift. None if abrupt.
        """
        super(AbruptDriftStream, self).__init__()

        stream = streams[0][2]
        self.abrupt = True
        self.drift_width = 0
        if width is not None:
            self.abrupt = False
            self.drift_width = width
        self.n_samples = length
        self.n_targets = stream.n_targets
        self.n_features = stream.n_features
        self.n_num_features = stream.n_num_features
        self.n_cat_features = stream.n_cat_features
        self.n_classes = stream.n_classes
        self.cat_features_idx = set(cat_features_idx) if cat_features_idx is not None else None
        self.feature_names = stream.feature_names
        self.target_names = stream.target_names
        self.target_values = stream.target_values
        self.n_targets = stream.n_targets
        self.target_values = set()
        for _, _, stream, _ in streams:
            try:
                stream_target_values = stream._get_target_values()
            except:
                stream_target_values = stream.target_values
            for stv in stream_target_values:
                t_val = stv
                if self.cat_features_idx is not None:
                    t_val = int(t_val)
                self.target_values.add(t_val)
        self.name = "AbruptStream"

        self.random_state = random_state
        self._random_state = None   # This is the actual random_state object used internally
        self.streams = streams
        self.length = length
        self.stream_idx = 0


        self._prepare_for_use()

    def _get_target_values(self):
        return self.target_values

    def _prepare_for_use(self):
        self._random_state = check_random_state(self.random_state)

    def prepare_for_use(self):
        self._prepare_for_use()

    def n_remaining_samples(self):
        """ Returns the estimated number of remaining samples.
        Returns
        -------
        int
            Remaining number of samples. -1 if infinite (e.g. generator)
        """
        return self.n_samples - self.sample_idx

    def has_more_samples(self):
        """ Checks if stream has more samples.
        Returns
        -------
        Boolean
            True if stream has more samples.
        """
        return self.n_remaining_samples() > 0

    def is_restartable(self):
        """ Determine if the stream is restartable.
         Returns
         -------
         Boolean
            True if stream is restartable.
         """
        return True

    def next_sample(self, batch_size=1):
        """ Returns next sample from the stream.
        Parameters
        ----------
        batch_size: int (optional, default=1)
            The number of samples to return.
        Returns
        -------
        tuple or tuple list
            Return a tuple with the features matrix
            for the batch_size samples that were requested.
        """
        self.current_sample_x = np.zeros((batch_size, self.n_features))
        self.current_sample_y = np.zeros((batch_size, self.n_targets)) if self.cat_features_idx is None else np.zeros((batch_size, self.n_targets), dtype=int)

        for j in range(batch_size):
            have_correct_concept = False
            while not have_correct_concept:
                current_concept = self.streams[self.stream_idx]
                if self.sample_idx > current_concept[1]:
                    self.stream_idx += 1
                elif self.sample_idx < current_concept[0]:
                    self.stream_idx -= 1
                else:
                    have_correct_concept = True

            if not self.abrupt:
                if self.stream_idx < len(self.streams)-1 and self.sample_idx > (current_concept[1] - self.drift_width / 2):
                    num_until_end = current_concept[1] - self.sample_idx
                    concept_chance = ((self.drift_width/ 2) + num_until_end) / self.drift_width
                    rand = self._random_state.rand()
                    if rand <= concept_chance:
                        have_correct_concept = True
                    else:
                        self.stream_idx += 1
                        current_concept = self.streams[self.stream_idx]
                if self.stream_idx > 0 and self.sample_idx < (current_concept[0] + self.drift_width / 2):
                    num_after_start = self.sample_idx - current_concept[0]
                    concept_chance = ((self.drift_width/ 2) + num_after_start) / self.drift_width
                    rand = self._random_state.rand()
                    if rand <= concept_chance:
                        have_correct_concept = True
                    else:
                        self.stream_idx -= 1
                        current_concept = self.streams[self.stream_idx]
            
            if current_concept[2].n_remaining_samples() == 0:
                current_concept[2].restart()
            
            X,y = current_concept[2].next_sample()

            if self.cat_features_idx is not None:
                new_batches = []
                for x in X:
                    new_x = []
                    for f_i, val in enumerate(x):
                        if f_i in self.cat_features_idx:
                            new_x.append(int(val))
                        else:
                            new_x.append(val)
                    new_x = np.array(new_x)
                    new_batches.append(new_x)
                X = np.array(new_batches)
                y = [int(y)]
                # print(y)

                


            self.current_sample_x[j, :] = X
            self.current_sample_y[j, :] = y
            # print(self.current_sample_y)
            self.sample_idx += 1

        return self.current_sample_x, self.current_sample_y.flatten()

    def restart(self):
        self._random_state = check_random_state(self.random_state)
        self.sample_idx = 0
        self.stream_idx = 0
        for s in self.streams:
            s.restart()

def RTREEGenerator(classification_function, random_state):
    return RandomTreeGenerator(tree_random_state=classification_function, sample_random_state=random_state)
def STAGGERGeneratorWrapper(classification_function, random_state):
    return STAGGERGenerator(classification_function=classification_function%3, random_state=random_state)
def SEAGeneratorWrapper(classification_function, random_state):
    return SEAGenerator(classification_function=classification_function%4, random_state=random_state)
def AGRAWALGeneratorWrapper(classification_function, random_state):
    return AGRAWALGenerator(classification_function=classification_function%10, random_state=random_state)
def windsimGeneratorWrapper(classification_function, random_state):
    return WindSimGenerator(concept=classification_function%4, sample_random_state=random_state)

def RTREESAMPLEGenerator(sampler_features, intra_concept_dist='dist', inter_concept_dist='uniform'):
    if sampler_features:
        return lambda classification_function, random_state: RandomTreeGeneratorSample(tree_random_state=classification_function, intra_concept_dist=intra_concept_dist, inter_concept_dist=inter_concept_dist, sampler_random_state = random_state, sampler_features = sampler_features, strength=1)
    return lambda classification_function, random_state: RandomTreeGeneratorSample(tree_random_state=classification_function, intra_concept_dist=intra_concept_dist, inter_concept_dist=inter_concept_dist, sampler_random_state = random_state, strength=1)

def HPLANESAMPLEGenerator(sampler_features):
    if sampler_features:
        return lambda classification_function, random_state: HyperplaneSampleGenerator(random_state=classification_function, n_features=8, n_drift_features=0, mag_change=0, sampler_random_state = random_state, sampler_features = sampler_features)
    return lambda classification_function, random_state: HyperplaneSampleGenerator(random_state=classification_function, n_features=8, n_drift_features=0, mag_change=0, sampler_random_state = random_state)

def HPLANEGenerator(classification_function, random_state):
    return HyperplaneGenerator(random_state=classification_function, n_features=8, n_drift_features=0, mag_change=0)

def RBFGenerator(classification_function, random_state):
    return RandomRBFGenerator(model_random_state=classification_function, sample_random_state=random_state)

def RBFGeneratorDifficulty(difficulty):
    n_centroids = difficulty * 5 + 15
    return lambda classification_function, random_state: RandomRBFGenerator(model_random_state=classification_function, sample_random_state=random_state, n_centroids=n_centroids, n_classes=4)

def RTREEGeneratorDifficulty(difficulty = 0):
    return lambda classification_function, random_state: RandomTreeGenerator(tree_random_state=classification_function, sample_random_state=random_state, max_tree_depth=difficulty+2, min_leaf_depth=difficulty)

def RTREESAMPLEGeneratorDifficulty(sampler_features, difficulty = 0, strength = 1):
    if sampler_features:
        return lambda classification_function, random_state: RandomTreeGeneratorSample(tree_random_state=classification_function, sampler_random_state = random_state, sampler_features = sampler_features, max_tree_depth=difficulty+2, min_leaf_depth=difficulty, strength = strength)
    return lambda classification_function, random_state: RandomTreeGeneratorSample(tree_random_state=classification_function, sampler_random_state = random_state, max_tree_depth=difficulty+2, min_leaf_depth=difficulty, strength = strength)
    

def get_concept_generator(name, difficulty):
    stream_generator = None
    num_concepts = None
    sampler_features = None
    if name == "STAGGER":
        stream_generator = STAGGERGeneratorWrapper
        num_concepts = 3
    if name == "STAGGERS":
        stream_generator = STAGGERGeneratorWrapper
        num_concepts = 3
    if name == "ARGWAL":
        stream_generator = AGRAWALGeneratorWrapper
        num_concepts = 10
    if name == "SEA":
        stream_generator = SEAGeneratorWrapper
        num_concepts = 10
    if name == "RTREE":
        stream_generator = RTREEGenerator
        num_concepts = 100
    if name == "WINDSIM":
        stream_generator = windsimGeneratorWrapper
        num_concepts = 4
    if name == "RTREEEasy":
        stream_generator = RTREEGeneratorDifficulty(difficulty=0)
        num_concepts = 100
    if name == "LM_RTREE":
        stream_generator = RTREEGeneratorDifficulty(difficulty=difficulty)
        num_concepts = 100
    if name == "LM_WINDSIM":
        stream_generator = windsimGeneratorWrapper
        num_concepts = 100
    if name == "LM_WINDSIM":
        stream_generator = windsimGeneratorWrapper
        num_concepts = 100
    if name == "RTREEEasySAMPLE":
        stream_generator = RTREESAMPLEGeneratorDifficulty(sampler_features, difficulty=0, strength=0.1)
        num_concepts = 100
    if name == "RTREEMedSAMPLE":
        stream_generator = RTREESAMPLEGeneratorDifficulty(sampler_features, difficulty=0, strength=0.2)
        num_concepts = 100
    if name == "RTREESAMPLE_HARD":
        stream_generator = RTREESAMPLEGeneratorDifficulty(sampler_features, difficulty=3, strength=0.4)
        num_concepts = 100
    if name == "RTREESAMPLE_Diff":
        print(f"Difficulty: {difficulty}")
        stream_generator = RTREESAMPLEGeneratorDifficulty(sampler_features, difficulty=difficulty, strength=0.4)
        num_concepts = 100
    if name == "SynEasyF":
        stream_generator = RTREESAMPLEGeneratorDifficulty(['frequency'], difficulty=0)
        num_concepts = 100
    if name == "SynEasyA":
        stream_generator = RTREESAMPLEGeneratorDifficulty(['autocorrelation'], difficulty=0)
        num_concepts = 100
    if name == "SynEasyD":
        stream_generator = RTREESAMPLEGeneratorDifficulty(['distribution'], difficulty=0)
        num_concepts = 100
    if name == "SynEasyAF":
        stream_generator = RTREESAMPLEGeneratorDifficulty(['autocorrelation', 'frequency'], difficulty=0)
        num_concepts = 100
    if name == "SynEasyDA":
        stream_generator = RTREESAMPLEGeneratorDifficulty(['distribution', 'autocorrelation'], difficulty=0)
        num_concepts = 100
    if name == "SynEasyDF":
        stream_generator = RTREESAMPLEGeneratorDifficulty(['distribution', 'frequency'], difficulty=0)
        num_concepts = 100
    if name == "SynEasyDAF":
        stream_generator = RTREESAMPLEGeneratorDifficulty(['distribution', 'autocorrelation', 'frequency'], difficulty=0)
        num_concepts = 100
    if name == "RTREESAMPLE":
        stream_generator = RTREESAMPLEGenerator(sampler_features)
        num_concepts = 100
    if name == "HPLANE":
        stream_generator = HPLANEGenerator
        num_concepts = 100
    if name == "RBF":
        stream_generator = RBFGenerator
        num_concepts = 100
    if name == "RBFEasy":
        stream_generator = RBFGeneratorDifficulty(difficulty=0)
        num_concepts = 100
    if name == "RBFMed":
        stream_generator = RBFGeneratorDifficulty(difficulty=2)
        num_concepts = 100
    if name == "HPLANESAMPLE":
        stream_generator = HPLANESAMPLEGenerator(sampler_features)
        num_concepts = 100
    if name == "RTREESAMPLE-UU":
        stream_generator = RTREESAMPLEGenerator(sampler_features, intra_concept_dist='uniform', inter_concept_dist='uniform')
        num_concepts = 100
    if name == "RTREESAMPLE-UN":
        stream_generator = RTREESAMPLEGenerator(sampler_features, intra_concept_dist='uniform', inter_concept_dist='norm')
        num_concepts = 100
    if name == "RTREESAMPLE-UD":
        stream_generator = RTREESAMPLEGenerator(sampler_features, intra_concept_dist='uniform', inter_concept_dist='dist')
        num_concepts = 100
    if name == "RTREESAMPLE-NU":
        stream_generator = RTREESAMPLEGenerator(sampler_features, intra_concept_dist='norm', inter_concept_dist='uniform')
        num_concepts = 100
    if name == "RTREESAMPLE-NN":
        stream_generator = RTREESAMPLEGenerator(sampler_features, intra_concept_dist='norm', inter_concept_dist='norm')
        num_concepts = 100
    if name == "RTREESAMPLE-ND":
        stream_generator = RTREESAMPLEGenerator(sampler_features, intra_concept_dist='norm', inter_concept_dist='dist')
        num_concepts = 100
    if name == "RTREESAMPLE-DU":
        stream_generator = RTREESAMPLEGenerator(sampler_features, intra_concept_dist='dist', inter_concept_dist='uniform')
        num_concepts = 100
    if name == "RTREESAMPLE-DN":
        stream_generator = RTREESAMPLEGenerator(sampler_features, intra_concept_dist='dist', inter_concept_dist='norm')
        num_concepts = 100
    if name == "RTREESAMPLE-DD":
        stream_generator = RTREESAMPLEGenerator(sampler_features, intra_concept_dist='dist', inter_concept_dist='dist')
        num_concepts = 100
    if name == "RTREESAMPLE-UB":
        stream_generator = RTREESAMPLEGenerator(sampler_features, intra_concept_dist='uniform', inter_concept_dist='bimodal')
        num_concepts = 100
    if name == "RTREESAMPLE-NB":
        stream_generator = RTREESAMPLEGenerator(sampler_features, intra_concept_dist='norm', inter_concept_dist='bimodal')
        num_concepts = 100
    if name == "RTREESAMPLE-DB":
        stream_generator = RTREESAMPLEGenerator(sampler_features, intra_concept_dist='dist', inter_concept_dist='bimodal')
        num_concepts = 100
    return stream_generator, num_concepts, sampler_features

def create_synthetic_concepts(path, name, seed, difficulty=None, n_concepts=100, init_concept_idx=0):
    """ Create preset synthetic concept generator
    """
    
    concept_idx = init_concept_idx
    stream_generator, num_concepts, sampler_features = get_concept_generator(name, difficulty)
    num_concepts = min(n_concepts, num_concepts)
    if stream_generator is None:
        raise ValueError("name not valid for a dataset")
    if seed is None:
        seed = np.random.randint(0, 1000)
    concepts = []
    for c in range(num_concepts):
        concept = stream_generator(classification_function = seed + concept_idx, random_state=seed + concept_idx)
        # with (path / f"concept_{concept_idx}.pickle").open("wb") as f:
        #     pickle.dump(concept, f)
        
        # if hasattr(concept, 'get_data'):
        #     with (path / f"data_{concept_idx}.json").open("w") as f:
        #         json.dump(concept.get_data(), f)
        concept_idx += 1
        concepts.append((concept, f"concept_{concept_idx}"))
    return concepts



def load_synthetic_concepts(name, seed, raw_data_path = None, difficulty_groups=None):
    data_path =  pathlib.Path(raw_data_path).resolve()
    concepts = []
    group_idx = 0
    concept_idx = 0
    for difficulty, n_concepts in difficulty_groups:
        diff_str = f"-{difficulty}" if difficulty is not None else ""
        file_path = data_path / name / "seeds" / f"{str(seed)}{diff_str}" 
        # if not file_path.exists():
        #     file_path.mkdir(parents=True, exist_ok=True)
        #     create_synthetic_concepts(file_path, name, seed, difficulty=difficulty, n_concepts=n_concepts)

        # concept_paths = list(file_path.glob('*concept*'))
        # if len(concept_paths) == 0:
        #     create_synthetic_concepts(file_path, name, seed, difficulty=difficulty, n_concepts=n_concepts)
        # concept_paths = list(file_path.glob('*concept*'))
        group_concept_generators = create_synthetic_concepts(file_path, name, seed, difficulty=difficulty, n_concepts=n_concepts, init_concept_idx=concept_idx)

        group_concepts = []
        for c, c_name in group_concept_generators:
            # with cp.open("rb") as f:
                # concepts.append((pickle.load(f), cp.stem))
            group_concepts.append((c, f"{c_name}-g-{group_idx}"))
            
            if len(group_concepts) >= n_concepts:
                break
        concepts += group_concepts
        concept_idx += len(group_concepts)
        group_idx += 1
    concepts = sorted(concepts, key=lambda x: x[1])
    return concepts

def create_real_concept(csv_name, name, seed, nrows = -1, sort_examples = False, inject_context=True):
    if nrows > 0:
        df = pd.read_csv(csv_name, nrows=nrows)
    else:
        df = pd.read_csv(csv_name)

    # Replace string categories with ints to work with scikit-multiflow
    # Also replace the last column with labels, unless we are not injecting context.
    # Then we do not, so we don't change the dataset.
    for c in df.columns:
        is_num = pd.api.types.is_numeric_dtype(df[c])
        if not is_num:
            codes, unique = pd.factorize(df[c])
            df[c] = codes
        elif c == df.columns[-1]:
            if inject_context:
                codes, unique = pd.factorize(df[c])
                df[c] = codes
            else:
                df[c] = df[c].astype(int)

    
    # If context is injected we can shuffle the order based on the seed to create randomness.
    # However, if context is already in the data we can't shuffle or we will destroy it
    if inject_context:
        df = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    
    # Remove initial index col
    if sort_examples:
        df = df[df.columns[1:]]

    stream = DataStream(df)
    if not name.parent.exists():
        name.parent.mkdir(parents=True, exist_ok=True)
    with name.open("wb") as f:
        pickle.dump(stream, f)
    return stream



def load_real_concepts(name, seed, raw_data_path = None, nrows = -1, sort_examples = False, inject_context=True):
    data_path =  pathlib.Path(raw_data_path)

    file_path = data_path / name

    concept_csv_paths = list(file_path.glob('*.csv'))
    for csv in concept_csv_paths:
        if csv.stem == 'context':
            continue
        concept_name = csv.parent / "seeds" / f"{seed}-{inject_context}" / f"concept_{csv.stem}.pickle"
        if not concept_name.exists() or True:
            create_real_concept(csv, concept_name, seed, nrows, sort_examples=sort_examples, inject_context=inject_context)
    
    seed_path = file_path / "seeds" / f"{seed}-{inject_context}"
    concept_paths = list(seed_path.glob('*concept*'))
    concepts = []
    for cp in concept_paths:
        if '_classes' in str(cp):
            continue
        with cp.open("rb") as f:
            concepts.append((pickle.load(f), cp.stem))
    concepts = sorted(concepts, key=lambda x: x[1])
    return concepts


def get_circular_fsm(seed, nconcepts, repeats, dropoff, nforward, noise):
    """ Create a transition pattern to test priors.
    A circular pattern is easy to ensure that all concepts have equal weighting.
    Three parameters determine the pattern, the drop off, or the probability of a transition to the direct neighbor,
    the number of possible forward skips, and noise, or random transitions.
    """
    if nconcepts < 2:
        return [0] * repeats
    total_occurences = nconcepts * repeats
    transition_probabilities = {}
    rng = np.random.RandomState(seed)
    for concept_idx in range(nconcepts):
        t_probs = {}
        # init noise probability for all concepts except current one
        for next_idx in range(nconcepts):
            if concept_idx == next_idx:
                continue
            t_probs[next_idx] = noise
        
        p = 1.0
        for i in range(1, nforward+1):
            next_idx = (concept_idx + i) % nconcepts
            if next_idx == concept_idx:
                break
            state_prob = (p*dropoff)
            p = p-state_prob
            t_probs[next_idx] = state_prob
        
        total_prob = sum(t_probs.values())
        for k in t_probs:
            t_probs[k] /= total_prob
        transition_probabilities[concept_idx] = t_probs
    
    current_concept = 0
    transition_pattern = [current_concept]
    while len(transition_pattern) < total_occurences:
        n_idx, probs = list(zip(*transition_probabilities[current_concept].items()))
        current_concept = rng.choice(n_idx, p=probs)
        transition_pattern.append(current_concept)
    
    return transition_pattern





def get_inorder_concept_ranges(concepts, seed, concept_length = 5000, repeats = 1, concept_max = -1, repeat_proportion = None, shuffle=True, dropoff=1.0, nforward=1, noise=0.0, boost_first_occurence = False):
    idx = 0
    positions = []
    if shuffle:
        shuffle_random_state = np.random.RandomState(seed)
        shuffle_random_state.shuffle(concepts)
    chosen_concepts = concepts[:min(len(concepts), concept_max)] if concept_max > 0 else concepts
    # print(chosen_concepts)
    pattern = get_circular_fsm(seed, len(chosen_concepts), repeats, dropoff, nforward, noise)
    seen_c_idx = set()
    for i, ci in enumerate(pattern):
        first_seen = ci not in seen_c_idx
        seen_c_idx.add(ci)
        c,n = concepts[ci]
        c_length = c.n_remaining_samples() if c.n_remaining_samples() != -1 else concept_length
        if repeat_proportion is not None:
            if repeat_proportion == -1:
                c_length = c_length / repeats
            else:
                c_length = c_length * repeat_proportion
        c_length = math.floor(c_length)
        if boost_first_occurence and first_seen:
            c_length *= 2
        start_idx = idx
        end_idx = start_idx + (c_length - 1)
        positions.append((start_idx, end_idx, c, n))
        idx = end_idx + 1
    return positions, idx

def stitch_concepts_inorder(concepts, concept_length = 10000):
    stream_A, n = concepts[0]
    stream_A.name = "A"
    stream_A_length = stream_A.n_remaining_samples() - 2 if stream_A.n_remaining_samples() != -1 else concept_length
    current_length = stream_A_length
    names = [(0, n)]
    
    for i in range(1, len(concepts)):
        stream_B, n = concepts[i]
        stream_B.name = "B"
        stream_B_length = stream_B.n_remaining_samples() - 2 if stream_B.n_remaining_samples() != -1 else concept_length
        new_stream = ConceptDriftStream(stream = stream_A, drift_stream= stream_B, position=current_length, width=1)
        stream_A = new_stream
        names.append((current_length, n))
        current_length += stream_B_length
    return stream_A, names, current_length


def sep_csv(name, raw_data_path = None, concept_col = 'author'):
    data_path =  pathlib.Path(raw_data_path) if raw_data_path is not None else (pathlib.Path.cwd() / __file__).parent.parent / "RawData" / "Real"

    file_path = data_path / name

    concept_csv_paths = list(file_path.glob('*.csv'))[0]
    df = pd.read_csv(concept_csv_paths)
    concepts = df[concept_col]
    concepts = concepts.unique()
    for c in concepts:
        filtered = df[df[concept_col] == c]
        filtered = filtered.drop(concept_col, axis = 1)
        shuffled = filtered.sample(frac=1)
        shuffled.to_csv(f"{concept_csv_paths.parent / concept_csv_paths.stem}_{c}.csv")

def load_real_datastream(name, stream_type, seed, raw_data_path = None):
    data_path =  pathlib.Path(raw_data_path) if raw_data_path is not None else (pathlib.Path.cwd() / __file__).parent.parent / "RawData" / "Real"

    file_path = data_path / name

    concept_csv_paths = list(file_path.glob('*.csv'))
    for csv in concept_csv_paths:
        concept_name = csv.parent / f"concept_{csv.stem}.pickle"
        stream = create_real_concept(csv, concept_name)
    return stream
    