import networkx as nx
import itertools
import numpy as np
from sklearn import metrics, manifold
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.datasets.samples_generator import make_blobs
import random
from copy import deepcopy
import time
from datetime import datetime
from matplotlib import pyplot as plt
import scipy as sp
from scipy import stats
from scipy.spatial import distance
from scipy.optimize import linear_sum_assignment

def GenerateGraph(proba, bigleavessizes):
    n = sum(bigleavessizes)
    G = nx.Graph()
    labels = []
    i = 0
    for lab in range(len(bigleavessizes)):
        for u in range(bigleavessizes[lab]):
            labels.append(lab)
            # print(lab)
            i += 1
    count = 0

    permuted = np.random.permutation(n)
    cpylabels = labels[:]
    labels = [cpylabels[permuted[x] - 1] for x in range(n)]

    for u, v in list(itertools.combinations_with_replacement(range(n), r=2)):
        clustu = labels[u]
        clustv = labels[v]
        coin = np.random.random()
        if coin < proba[clustu][clustv]:
            count = count + 1
            G.add_edge(u, v, weight=1.0)

    #print("Number of edges:", count)
    return G, labels


def binarylimitsspecial(n, k, T, p, q, verbose=True):
    """
    Compare the ECC basic approach to PCA on the stochastic block model with k equal-size clusters
    :param n: number of nodes
    :param k: number of clusters --> each cluster has size n/k
    :param T: length of the simple code
    :param verbose: set to false to avoid printing detailed results
    :return:
    """
    if verbose: print("PARAMS", n, k)
    Matrix = np.tile(q, [k, k])
    np.fill_diagonal(Matrix, p)
    bigleavessizes = [int(n / k)] * k

    intra = sp.linalg.block_diag(*[distance.squareform(np.random.binomial(1, p, int(d * (d-1) / 2))) for _, d in enumerate(bigleavessizes)])
    intra_mask = sp.linalg.block_diag(*[np.ones((d, d)) for _, d in enumerate(bigleavessizes)])
    intra_fin = np.multiply(intra, intra_mask)
    inter = distance.squareform(np.random.binomial(1, q, int(n*(n-1)/2)))
    inter_mask = np.ones((n, n)) - intra_mask
    inter_fin = np.multiply(inter, inter_mask)
    X = intra_fin + inter_fin

    if verbose:
        print("Probability Matrix:")
        print(np.matrix(Matrix))

    labels = np.hstack([[i] * (int(n / k)) for i in range(k)])

    if verbose: print("Generation done.")
    #embedding = manifold.MDS(n_components=n)
    #X = embedding.fit_transform(X)
    return compute_all_kmeans(X, T, k, labels, verbose)


def apply_on_blobs(n, k, T, p, verbose=True):
    """
    :param n: number of points
    :param k: for k-means
    :param T: ECC code length
    :param p: blob STD
    :param verbose:
    :return:
    """
    X, labels = make_blobs(n_samples=n, centers=k, cluster_std=p)
    if verbose:
        plt.scatter(X[:, 0], X[:, 1], c=labels)
    return compute_all_kmeans(X, T, k, labels, verbose)


def correct_label_assignment(cluster_labels, true_labels):
    conf_mat = metrics.confusion_matrix(true_labels, cluster_labels)
    # hungarian algorithm to assign optimal cluster ids to original labels
    _, idmap = linear_sum_assignment(1 / (1 + conf_mat))
    nbrs = dict([(id, v) for v, id in enumerate(idmap)])
    return np.asarray([nbrs[v] for v in cluster_labels]), conf_mat


def compute_all_kmeans(X, T, k, labels, verbose=True):
    """
    :param X: array shape=(n_samples, n_features)
    :param T: ECC code length
    :param k: for k-means
    :param labels: ground truth cluster ids
    :param verbose: print details
    :return: acc_alg, acc_pca, acc_vanilla
    """
    n = X.shape[0]
    ### Error Correcting Code approach
    tic = time.time()
    np.random.seed(int(time.time()))
    random_subsets = np.random.randint(0, 2, (n, T))
    parity_bits = np.mod(np.matmul(X, random_subsets), 2)
    reduced_data = np.hstack([X, parity_bits])
    kmeans_clusters_alg, conf_mat = correct_label_assignment(kmeans(reduced_data, k), labels)

    acc_alg = metrics.classification.accuracy_score(labels, kmeans_clusters_alg)
    print("ALG took %.3s seconds. Accuracy=%s" % (time.time() - tic, acc_alg))
    if verbose:
        print(metrics.classification.classification_report(labels, kmeans_clusters_alg))
        print(metrics.confusion_matrix(labels, kmeans_clusters_alg))

    ### Classic PCA approach
    tic = time.time()
    reduced_data2 = PCA().fit_transform(X)
    kmeans_clusters_standard, conf_mat2 = correct_label_assignment(kmeans(reduced_data2, k), labels)
    acc_pca = metrics.classification.accuracy_score(labels, kmeans_clusters_standard)
    print("PCA (%s components) took %.3s seconds. Accuracy=%s" % (n, time.time() - tic, acc_pca))
    if verbose:
        print(metrics.classification.classification_report(labels, kmeans_clusters_standard))
        print(metrics.confusion_matrix(labels, kmeans_clusters_standard))

    ### Vanilla k-means approach
    tic = time.time()
    reduced_data3 = X
    kmeans_clusters_vanilla, conf_mat3 = correct_label_assignment(kmeans(reduced_data3, k), labels)
    acc_vanilla = metrics.classification.accuracy_score(labels, kmeans_clusters_vanilla)
    print("Vanilla k-means took %.3s seconds. Accuracy=%s" % (time.time() - tic, acc_vanilla))
    if verbose:
        print(metrics.classification.classification_report(labels, kmeans_clusters_vanilla))
        print(metrics.confusion_matrix(labels, kmeans_clusters_vanilla))

    return acc_alg, acc_pca, acc_vanilla


def classif_error(labels):
    nb_correct_class = 0
    # for
    n = len(labels)
    for i in range(len(labels)):
        if i < n / 4 and labels[i] == 0:
            nb_correct_class += 1
        if i >= n / 2 and labels[i] == 1:
            nb_correct_class += 1
    return (nb_correct_class / n)


def check_labels(clustering, labels):
    nb_correct_class = 0
    for c in range(len(clustering)):
        if clustering[c] - 1 == labels[c]:
            nb_correct_class += 1
    return nb_correct_class


def kmeans(X, k):
    alg = KMeans(init='k-means++', n_clusters=k, n_init=10)
    alg.fit(X)
    # kmeans_clusters = {c: [] for c in range(k)}
    # for i in range(len(X)):
    #    kmeans_clusters[alg.labels_[i]].append(i)
    return alg.labels_


def check_clusters(clusters, labels):
    predict = [0] * len(labels)
    bad_guys = []

    nb_correctly_classified = 0
    for c in clusters:
        if clusters[c] == []: continue
        nbrs = {}
        for p in clusters[c]:
            if labels[p] in nbrs:
                nbrs[labels[p]] += 1
            else:
                nbrs[labels[p]] = 1
        M = 0
        digit = -1
        for n in nbrs:
            if nbrs[n] > M:
                digit = n
                M = nbrs[n]

        for p in clusters[c]:
            if labels[p] != digit:
                bad_guys.append(p)

        nb_correctly_classified += nbrs[digit]
        # if digit == -1:
        #     print(clusters[c], nbrs)
        print("Cluster", c, "represents digit", digit)
        for p in clusters[c]:
            predict[p] = digit
        print("           Classification accuracy = ",
              100 * nbrs[digit] / len(clusters[c]), "%.")
    print("Overall accuracy :",
          nb_correctly_classified / len(labels))
    return bad_guys


def digits(T=64, plotresult=False):
    '''
    compares the basic ECC approach to PCA on the classic digits dataset of scikit-learn
    (https://scikit-learn.org/stable/auto_examples/cluster/plot_kmeans_digits.html)
    :param T:
    :param plotresult:
    :return:
    '''
    from sklearn import datasets
    digits = datasets.load_digits()
    labels = digits.target

    ### Classic PCA
    X = digits.data
    X_reduced = PCA(n_components=2).fit_transform(X)
    kmeans_clusters = kmeans(X_reduced, 10)
    print("Kmean classification:")
    check_clusters(kmeans_clusters, labels)

    ### Error Correcting Code approach
    n = len(labels)
    random.seed(datetime.now())
    vects = []
    for step in range(T):
        v = []
        for c in range(n):
            a = random.uniform(0, 1)
            if a == 1:
                v.append(1)
            else:
                v.append(0)
        vects.append(v)

    Y_large = digits.data
    Y_reduced = PCA(n_components=2).fit_transform(Y_large)

    Y_new = []
    for row in Y_reduced:
        # print(row)
        a = deepcopy(row)
        # print(row)
        for j in range(T):
            s = sum([row[i] for i in range(len(row))
                     if vects[j][i] == 1])
            a = a + [s % 199]
        Y_new.append(a)

    Y_new_reduced = Y_new
    kmeans_clusters_alg = kmeans(Y_new_reduced, 10)
    print("New Alg classification:")
    bad_guys = check_clusters(kmeans_clusters_alg, labels)

    ### PLOT Result
    ###
    if not plotresult: return
    import matplotlib.pyplot as plt
    colors = ['g', 'b', 'c', 'm', 'y', 'k']

    print(len(labels))
    for gc in kmeans_clusters_alg:
        for x in kmeans_clusters_alg[gc]:
            plt.plot(Y_new_reduced[x][0],
                     Y_new_reduced[x][1], colors[gc % 6] + 'o')

    for x in bad_guys:
        plt.plot(Y_new_reduced[x][0], Y_new_reduced[x][1],
                 "ro")

    plt.axis([-50, 50, -50, 50])
    plt.show()


def wrapper(n):
    runs = 50
    #p = 1 / 10  # log(n)/sqrt(n)
    #q = 1 / 200  # log(n)/(10*sqrt(n))
    p, q = 0.01, 0.003
    T = int(0.1 * n)# int(n*(n-1)/2)
    #p, q = 0.01, 0.003
    res = list()
    for step in range(runs):
        print('iter #%s' % step)
        res.append(binarylimitsspecial(n, 4, T, p, q, runs < 5))
    res = np.asarray(res)
    plt.boxplot(res, notch=True, labels=['ALG', 'PCA', 'VANILLA'])
    plt.ylabel('Clustering accuracy')
    anovap = stats.f_oneway(res[:, 0], res[:, 1], res[:, 2])
    plt.title('Comparing %s runs at n=%s p=%s q=%s T=%s p-value(anova)=%.2E' % (runs, n, p, q, T, anovap.pvalue))
    plt.savefig('results_%s_%s_%s.png' % (n, p, q))
    plt.show()

### SBM
wrapper(600)

### Digits
# digits()
