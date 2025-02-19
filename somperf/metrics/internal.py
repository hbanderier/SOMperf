"""
Internal indices
"""

import numpy as np
from typing import Callable, Tuple
from nptyping import NDArray, Float, Int, Shape
from sklearn.metrics.pairwise import euclidean_distances
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import shortest_path
import pandas as pd


def c_measure(
    precomputed_distances: NDArray[Shape["*, *"], Int],
    x: NDArray[Shape["*, *"], Float],
    som: NDArray[Shape["*, *"], Float] = None,
    d: NDArray[Shape["*, *"], Float] = None,
) -> float:
    """C measure.

    Measures distance preservation between input space and output space. Euclidean distance is used in input space.
    In output space, distance is usually Manhattan distance between the best matching units on the maps (this distance
    is provided by the dist_fun argument).

    Parameters
    ----------
    precomputed_distances : array, shape = [nx, ny]
        pairwise distances between units on the map.
    x : array, shape = [n_samples, dim]
        input samples.
    som : array, shape = [n_units, dim]
        (optional) SOM code vectors.
    d : array, shape = [n_samples, n_units]
        (optional) euclidean distances between input samples and code vectors.

    Returns
    -------
    c : float
        C measure (higher is better)

    References
    ----------
    Goodhill, G. J., & Sejnowski, T. J. (1996). Quantifying neighbourhood preservation in topographic mappings.
    """
    n = x.shape[0]
    if d is None:
        if som is None:
            raise ValueError("If distance matrix d is not given, som cannot be None!")
        else:
            d = euclidean_distances(x, som)
    d_data = euclidean_distances(x)
    bmus = np.argmin(d, axis=1)
    d_som = precomputed_distances[bmus[:, None], bmus[None, :]].astype(np.float64)
    return np.sum(d_data * d_som) / 2.0  # should be normalized by n(n-1) ?


def combined_error(
    precomputed_distances: NDArray[Shape["*, *"], Int],
    som: NDArray[Shape["*, *"], Float],
    x: NDArray[Shape["*, *"], Float] = None,
    d: NDArray[Shape["*, *"], Float] = None,
) -> float:
    """Combined error.

    Parameters
    ----------
    precomputed_distances : array, shape = [nx, ny]
        pairwise distances between units on the map.
    som : array, shape = [n_units, dim]
        SOM code vectors.
    x : array, shape = [n_samples, dim]
        (optional) input samples.
    d : array, shape = [n_samples, n_units]
        (optional) euclidean distances between input samples and code vectors.

    Returns
    -------
    ce : float
        combined error  (lower is better)

    References
    ----------
    Kaski, S., & Lagus, K. (1996). Comparing Self-Organizing Maps.
    """
    if d is None:
        if x is None:
            raise ValueError("If distance matrix d is not given, x cannot be None!")
        else:
            d = euclidean_distances(x, som)
    # pairwise euclidean distances between neighboring SOM prototypes
    # distances between non-neighboring units are set to inf to force the path to follow neighboring units
    d_som = csr_matrix(
        np.where(
            precomputed_distances == 1,
            np.sqrt(np.sum((som[None, ...] - som[:, None, ...]) ** 2, axis=-1)),
            np.inf,
        )
    )
    tbmus = np.argsort(d, axis=1)[:, :2]  # two best matching units
    ces = np.zeros(d.shape[0])
    for i in range(d.shape[0]):
        ces[i] = d[i, tbmus[i, 0]]
        if (
            precomputed_distances[tbmus[i, 0], tbmus[i, 1]] == 1
        ):  # if BMUs are neighbors
            ces[i] += d_som[tbmus[i, 0], tbmus[i, 1]]
        else:
            ces[i] += shortest_path(
                csgraph=d_som,
                method="auto",
                directed=False,
                return_predecessors=False,
                indices=tbmus[i, 0],
            )[tbmus[i, 1]]
    return np.mean(ces)


def distortion(
    precomputed_distances: NDArray[Shape["*, *"], Int],
    neighborhood_fun: Callable,
    som: NDArray[Shape["*, *"], Float],
    x: NDArray[Shape["*, *"], Float] = None,
    d: NDArray[Shape["*, *"], Float] = None,
) -> float:
    """Distortion (SOM loss function).

    Computes distortion, which is the loss function minimized by the SOM learning algorithm.
    It consists in a sum of squared euclidean distances between samples and SOM prototypes, weighted
    by a neighborhood function that depends on the distances to the best-matching unit on the map.

    Parameters
    ----------
    precomputed_distances : array, shape = [nx, ny]
        pairwise distances between units on the map.
    neighborhood_fun : function (d : int) => float in [0,1]
        neighborhood function, equal to 1 when d = 0 and decreasing with d.
    som : array, shape = [n_units, dim]
        (optional) SOM code vectors.
    x : array, shape = [n_samples, dim]
        (optional) input samples.
    d : array, shape = [n_samples, n_units]
        (optional) euclidean distances between input samples and code vectors.

    Returns
    -------
    distortion : float
        distortion error (lower is better)
    """
    if d is None:
        if som is None or x is None:
            raise ValueError(
                "If distance matrix d is not given, som and x cannot be None!"
            )
        else:
            d = euclidean_distances(x, som)
    bmus = np.argmin(d, axis=1)
    weights = neighborhood_fun(precomputed_distances[bmus, : d.shape[1]])
    distortions = np.sum(weights * np.square(d), axis=1)
    return np.mean(distortions)


def kruskal_shepard_error(
    precomputed_distances: NDArray[Shape["*, *"], Int],
    x: NDArray[Shape["*, *"], Float],
    som: NDArray[Shape["*, *"], Float] = None,
    d: NDArray[Shape["*, *"], Float] = None,
) -> float:
    """Kruskal-Shepard error.
    Measures distance preservation between input space and output space. Euclidean distance is used in input space.
    In output space, distance is usually Manhattan distance between the best matching units on the maps (this distance
    is provided by the dist_fun argument).
    Parameters
    ----------
    precomputed_distances : array, shape = [nx, ny]
        pairwise distances between units on the map.
    x : array, shape = [n_samples, dim]
        input samples.
    som : array, shape = [n_units, dim]
        (optional) SOM code vectors.
    d : array, shape = [n_samples, n_units]
        (optional) euclidean distances between input samples and code vectors.
    Returns
    -------
    kse : float
        Kruskal-Shepard error (lower is better)
    References
    ----------
    Kruskal, J.B. (1964). Multidimensional scaling by optimizing goodness of fit to a nonmetric hypothesis.
    Elend, L., & Kramer, O. (2019). Self-Organizing Maps with Convolutional Layers.
    """
    n = x.shape[0]
    if d is None:
        if som is None:
            raise ValueError("If distance matrix d is not given, som cannot be None!")
        else:
            d = euclidean_distances(x, som)
    d_data = euclidean_distances(x)
    d_data /= d_data.max()
    bmus = np.argmin(d, axis=1)
    d_som = precomputed_distances[bmus[:, None], bmus[None, :]].astype(np.float64)
    d_som /= d_som.max()
    return np.sum(np.square(d_data - d_som)) / (n**2 - n)


def neighborhood_preservation(
    k: int,
    som: NDArray[Shape["*, *"], Float],
    x: NDArray[Shape["*, *"], Float],
    d: NDArray[Shape["*, *"], Float] = None,
) -> float:
    """Neighborhood preservation of SOM map.

    Parameters
    ----------
    k : int
        number of neighbors. Must be < n // 2 where n is the data size.
    som : array, shape = [n_units, dim]
        SOM code vectors.
    x : array, shape = [n_samples, dim]
        input samples.
    d : array, shape = [n_samples, n_units]
        (optional) euclidean distances between input samples and code vectors.

    Returns
    -------
    np : float in [0, 1]
        neighborhood preservation measure (higher is better)

    References
    ----------
    Venna, J., & Kaski, S. (2001). Neighborhood preservation in nonlinear projection methods: An experimental study.
    """
    n = x.shape[0]  # data size
    assert k < (
        n / 2
    ), "Number of neighbors k must be < N/2 (where N is the number of data samples)."
    if d is None:
        d = euclidean_distances(x, som)
    d_data = euclidean_distances(x) + np.diag(np.inf * np.ones(n))
    projections = som[np.argmin(d, axis=1)]
    d_projections = euclidean_distances(projections) + np.diag(np.inf * np.ones(n))
    original_ranks = pd.DataFrame(d_data).rank(method="min", axis=1)
    projected_ranks = pd.DataFrame(d_projections).rank(method="min", axis=1)
    weights = (projected_ranks <= k).sum(axis=1) / (original_ranks <= k).sum(
        axis=1
    )  # weight k-NN ties
    mask0 = np.eye(n, dtype=bool)
    mask1 = (original_ranks.values <= k) & (projected_ranks.values > k)

    arr0 = (projected_ranks.values - k) * weights.values[:, None]
    arr0[mask0 | ~mask1] = 0

    nps = np.sum(arr0, axis=1)

    return 1.0 - 2.0 / (n * k * (2 * n - 3 * k - 1)) * np.sum(nps)


def neighborhood_preservation_trustworthiness(
    k: int,
    som: NDArray[Shape["*, *"], Float],
    x: NDArray[Shape["*, *"], Float],
    d: NDArray[Shape["*, *"], Float] = None,
) -> Tuple[float, float]:
    """Neighborhood preservation and trustworthiness of SOM map.
    Parameters
    ----------
    k : int
        number of neighbors. Must be < n // 2 where n is the data size.
    som : array, shape = [n_units, dim]
        SOM code vectors.
    x : array, shape = [n_samples, dim]
        input samples.
    d : array, shape = [n_samples, n_units]
        (optional) euclidean distances between input samples and code vectors.
    Returns
    -------
    npr, tr : float tuple in [0, 1]
        neighborhood preservation and trustworthiness measures (higher is better)
    References
    ----------
    Venna, J., & Kaski, S. (2001). Neighborhood preservation in nonlinear projection methods: An experimental study.
    """
    n = x.shape[0]  # data size
    assert k < (
        n / 2
    ), "Number of neighbors k must be < N/2 (where N is the number of data samples)."
    if d is None:
        d = euclidean_distances(x, som)

    d_data = euclidean_distances(x) + np.diag(np.inf * np.ones(n))
    projections = som[np.argmin(d, axis=1)]
    d_projections = euclidean_distances(projections) + np.diag(np.inf * np.ones(n))
    original_ranks = pd.DataFrame(d_data).rank(method="min", axis=1)
    projected_ranks = pd.DataFrame(d_projections).rank(method="min", axis=1)
    weights = (projected_ranks <= k).sum(axis=1) / (original_ranks <= k).sum(
        axis=1
    )  # weight k-NN ties

    mask0 = np.eye(n, dtype=bool)
    mask1 = (original_ranks.values <= k) & (projected_ranks.values > k)
    mask2 = (original_ranks.values > k) & (projected_ranks.values <= k)

    arr0 = (projected_ranks.values - k) * weights.values[:, None]
    arr0[mask0 | ~mask1] = 0

    arr1 = (original_ranks.values - k) / weights.values[:, None]
    arr1[mask0 | ~mask2] = 0

    trs = np.sum(arr1, axis=1)
    nps = np.sum(arr0, axis=1)

    npr = 1.0 - 2.0 / (n * k * (2 * n - 3 * k - 1)) * np.sum(nps)
    tr = 1.0 - 2.0 / (n * k * (2 * n - 3 * k - 1)) * np.sum(trs)
    return npr, tr


def quantization_error(
    som: NDArray[Shape["*, *"], Float] = None,
    x: NDArray[Shape["*, *"], Float] = None,
    d: NDArray[Shape["*, *"], Float] = None,
) -> float:
    """Quantization error.

    Computes mean quantization error with euclidean distance.

    Parameters
    ----------
    som : array, shape = [n_units, dim]
        (optional) SOM code vectors.
    x : array, shape = [n_samples, dim]
        (optional) input samples.
    d : array, shape = [n_samples, n_units]
        (optional) euclidean distances between input samples and code vectors.

    Returns
    -------
    qe : float
        quantization error (lower is better)
    """
    if d is None:
        if som is None or x is None:
            raise ValueError(
                "If distance matrix d is not given, som and x cannot be None!"
            )
        else:
            d = euclidean_distances(x, som)
    qes = np.min(d, axis=1)
    return np.mean(qes)


def topographic_error(
    precomputed_distances: NDArray[Shape["*, *"], Int],
    x: NDArray[Shape["*, *"], Float] = None,
    som: NDArray[Shape["*, *"], Float] = None,
    d: NDArray[Shape["*, *"], Float] = None,
) -> float:
    """SOM topographic error.

    Topographic error is the ratio of data points for which the two best matching units are not neighbors on the map.

    Parameters
    ----------
    precomputed_distances : array, shape = [nx, ny]
        pairwise distances between units on the map.
    som : array, shape = [n_units, dim]
        (optional) SOM code vectors.
    x : array, shape = [n_samples, dim]
        (optional) input samples.
    d : array, shape = [n_samples, n_units]
        (optional) euclidean distances between input samples and code vectors.

    Returns
    -------
    te : float in [0, 1]
        topographic error (lower is better)
    """
    if d is None:
        if som is None or x is None:
            raise ValueError(
                "If distance matrix d is not given, som and x cannot be None!"
            )
        else:
            d = euclidean_distances(x, som)
    tbmus = np.argsort(d, axis=1)[:, :2]  # two best matching units
    tes = precomputed_distances[tbmus[:, 0], tbmus[:, 1]] > 1
    return np.mean(tes)


def topographic_function(ks, dist_fun, max_dist, som=None, x=None, d=None, som_dim=2):
    """Normalized topographic function.

    Parameters
    ----------
    ks: array
        topographic function parameters. Must be normalized distances, i.e. k=d/max_dist where d is a distance
        on the map and max_dist is the maximum distance between two units on the map.
    dist_fun : function (k : int, l : int) => int
        distance function between units k and l on the map.
    max_dist : int
        maximum distance on the map.
    som : array, shape = [n_units, dim]
        (optional) SOM code vectors.
    x : array, shape = [n_samples, dim]
        (optional) input samples.
    d : array, shape = [n_samples, n_units]
        (optional) euclidean distances between input samples and code vectors.
    som_dim : int (default=2)
        number of dimensions of the SOM grid

    Returns
    -------
    tf : array
        topographic function taken at values ks

    References
    ----------
    Villmann, T., Der, R., & Martinetz, T. (1994). A New Quantitative Measure of Topology Preservation in Kohonen’s Feature Maps.
    """
    if d is None:
        if som is None or x is None:
            raise ValueError(
                "If distance matrix d is not given, som and x cannot be None!"
            )
        else:
            d = euclidean_distances(x, som)
    tbmus = np.argsort(d, axis=1)[:, :2]  # two best matching units
    n_units = d.shape[1]
    C = np.zeros((n_units, n_units), dtype="int")  # connectivity matrix
    for tbmu in tbmus:
        C[tbmu[0], tbmu[1]] = 1
        C[tbmu[1], tbmu[0]] = 1
    tf = np.zeros(len(ks))
    for c in range(n_units):
        for cc in range(n_units):
            for i, k in enumerate(ks):
                if dist_fun(c, cc) / max_dist > k and C[c, cc] == 1:
                    tf[i] += 1
    return tf / (n_units * (n_units - 3**som_dim))


def topographic_product(dist_fun, som):
    """Topographic product.

    Parameters
    ----------
    dist_fun : function (k : int, l : int) => int
        distance function between units k and l on the map.
    som : array, shape = [n_units, dim]
        SOM code vectors.

    Returns
    -------
    tp : float
        topographic product (tp < 0 when the map is too small, tp > 0 if it is too large)

    References
    ----------
    Bauer, H. U., & Pawelzik, K. R. (1992). Quantifying the Neighborhood Preservation of Self-Organizing Feature Maps.
    """
    n_units = som.shape[0]
    original_d = euclidean_distances(som) + 1e-16
    original_knn = np.argsort(original_d, axis=1)
    map_d = (
        np.array([[dist_fun(j, k) for k in range(n_units)] for j in range(n_units)])
        + 1e-16
    )
    map_knn = np.argsort(map_d, axis=1)
    # compute Q1 (n_units x n_units-1 matrix)
    q1 = np.array(
        [
            [
                np.divide(
                    original_d[j, map_knn[j, k]], original_d[j, original_knn[j, k]]
                )
                for k in range(1, n_units)
            ]
            for j in range(n_units)
        ]
    )
    # compute Q2 (n_units x n_units-1 matrix)
    q2 = np.array(
        [
            [
                np.divide(map_d[j, map_knn[j, k]], map_d[j, original_knn[j, k]])
                for k in range(1, n_units)
            ]
            for j in range(n_units)
        ]
    )
    # compute P3 (n_units x n_units-1 matrix)
    p3 = np.array(
        [
            [
                np.prod([(q1[j, l] * q2[j, l]) ** (1 / (2 * k)) for l in range(k)])
                for k in range(1, n_units)
            ]
            for j in range(n_units)
        ]
    )
    # combine final result (float)
    return np.sum(np.log(p3)) / (n_units * (n_units - 1))


def trustworthiness(
    k: int,
    som: NDArray[Shape["*, *"], Float],
    x: NDArray[Shape["*, *"], Float],
    d: NDArray[Shape["*, *"], Float] = None,
) -> Tuple[float, float]:
    """Trustworthiness of SOM map.
    Parameters
    ----------
    k : int
        number of neighbors. Must be < n // 2 where n is the data size.
    som : array, shape = [n_units, dim]
        SOM code vectors.
    x : array, shape = [n_samples, dim]
        input samples.
    d : array, shape = [n_samples, n_units]
        (optional) euclidean distances between input samples and code vectors.
    Returns
    -------
    tr : float in [0, 1]
        trustworthiness measure (higher is better)
    References
    ----------
    Venna, J., & Kaski, S. (2001). Neighborhood preservation in nonlinear projection methods: An experimental study.
    """
    n = x.shape[0]  # data size
    assert k < (
        n / 2
    ), "Number of neighbors k must be < N/2 (where N is the number of data samples)."
    if d is None:
        d = euclidean_distances(x, som)

    d_data = euclidean_distances(x) + np.diag(np.inf * np.ones(n))
    projections = som[np.argmin(d, axis=1)]
    d_projections = euclidean_distances(projections) + np.diag(np.inf * np.ones(n))
    original_ranks = pd.DataFrame(d_data).rank(method="min", axis=1)
    projected_ranks = pd.DataFrame(d_projections).rank(method="min", axis=1)
    weights = (projected_ranks <= k).sum(axis=1) / (original_ranks <= k).sum(
        axis=1
    )  # weight k-NN ties

    mask0 = np.eye(n, dtype=bool)
    mask2 = (original_ranks.values > k) & (projected_ranks.values <= k)

    arr1 = (original_ranks.values - k) / weights.values[:, None]
    arr1[mask0 | ~mask2] = 0

    trs = np.sum(arr1, axis=1)

    return 1.0 - 2.0 / (n * k * (2 * n - 3 * k - 1)) * np.sum(trs)

