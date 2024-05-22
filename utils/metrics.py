import numpy as np
import scipy
import os
from tqdm import tqdm

import torch
from torch_geometric.utils import to_dense_adj, degree
import torch.nn.functional as F


def compute_distance_matrix(embedding1, embedding2, dist_type='l1'):
    """
    Compute distance matrix between two sets of embeddings
    :param embedding1: node embeddings 1
    :param embedding2: node embeddings 2
    :param dist_type: distance function
    :return: distance matrix
    """
    assert dist_type in ['l1', 'cosine'], 'Similarity function not supported'

    if dist_type == 'l1':
        return scipy.spatial.distance.cdist(embedding1, embedding2, metric='cityblock')
    elif dist_type == 'cosine':
        return scipy.spatial.distance.cdist(embedding1, embedding2, metric='cosine')


def compute_ot_cost_matrix(G1_data, G2_data, alpha=0.1):
    """
    Compute optimal transport cost matrix between two sets of embeddings
    :param G1_data: PyG Data object for graph 1
    :param G2_data: PyG Data object for graph 2
    :param alpha: trade-off parameter
    :return: cost_rwr: cost matrix
    """

    r1, r2 = G1_data.dists, G2_data.dists
    x1, x2 = G1_data.x, G2_data.x

    r1, r2 = F.normalize(r1, p=2, dim=1), F.normalize(r2, p=2, dim=1)
    x1, x2 = F.normalize(x1, p=2, dim=1), F.normalize(x2, p=2, dim=1)

    cost_node = alpha * torch.exp(-(r1 @ r2.T)) + (1 - alpha) * torch.exp(-(x1 @ x2.T))

    return cost_node


def compute_metrics(distances1, distances2, test_pairs, hit_top_ks=(1, 5, 10, 30, 50, 100)):
    """
    Compute metrics for the model (HITS@k, MRR)
    :param distances1: distance matrix 1 (G1 to G2)
    :param distances2: distance matrix 2 (G2 to G1)
    :param test_pairs: test pairs
    :param hit_top_ks: list of k for HITS@k
    :return:
        hits: HITS@k
        mrr: MRR
    """

    hits = {}

    ranks1 = torch.argsort(torch.from_numpy(distances1), dim=1).numpy()
    ranks2 = torch.argsort(torch.from_numpy(distances2), dim=1).numpy()

    signal1_hit = ranks1[:, :hit_top_ks[-1]] == np.expand_dims(test_pairs[:, 1], -1)
    signal2_hit = ranks2[:, :hit_top_ks[-1]] == np.expand_dims(test_pairs[:, 0], -1)
    for k in hit_top_ks:
        hits_ltr = np.sum(signal1_hit[:, :k]) / test_pairs.shape[0]
        hits_rtl = np.sum(signal2_hit[:, :k]) / test_pairs.shape[0]
        hits[k] = max(hits_ltr, hits_rtl)

    mrr_ltr = np.mean(1 / (np.where(ranks1 == np.expand_dims(test_pairs[:, 1], -1))[1] + 1))
    mrr_rtl = np.mean(1 / (np.where(ranks2 == np.expand_dims(test_pairs[:, 0], -1))[1] + 1))
    mrr = max(mrr_ltr, mrr_rtl)

    return hits, mrr


def log_path(dataset):
    if not os.path.exists(f'logs/{dataset}_results'):
        os.makedirs(f'logs/{dataset}_results')
    runs = len([f for f in os.listdir(f'logs/{dataset}_results') if os.path.isdir(f'logs/{dataset}_results/{f}')])
    return f'logs/{dataset}_results/run_{runs}'
