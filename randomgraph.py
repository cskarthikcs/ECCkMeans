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
import generate_BX_graph as BX
import mushrooms as mush
#from CTA.BCHCode zimport BCHCode #borrowed from https://github.com/christiansiegel/coding-theory-algorithms

def generate_block_stochastic_data(n, k, p, q):
    bigleavessizes = [int(n / k)] * k
    intra = sp.linalg.block_diag(*[distance.squareform(np.random.binomial(1, p, int(d * (d-1) / 2))) for _, d in enumerate(bigleavessizes)])
    intra_mask = sp.linalg.block_diag(*[np.ones((d, d)) for _, d in enumerate(bigleavessizes)])
    intra_fin = np.multiply(intra, intra_mask)
    inter = distance.squareform(np.random.binomial(1, q, int(n*(n-1)/2)))
    inter_mask = np.ones((n, n)) - intra_mask
    inter_fin = np.multiply(inter, inter_mask)
    X = intra_fin + inter_fin
    labels = np.hstack([[i] * (int(n / k)) for i in range(k)])
    return X, labels

def binarylimitsspecial(n, k, T, p, q, s=.5, verbose=True):
    """
    Compare the ECC basic approach to PCA on the stochastic block model with k equal-size clusters
    :param n: number of nodes
    :param k: number of clusters --> each cluster has size n/k
    :param T: length of the simple code
    :param verbose: set to false to avoid printing detailed results
    :return:
    """
    if verbose: print("PARAMS", n, k)
    X, labels = generate_block_stochastic_data(n, k, T, p, q)

    if verbose: print("Generation done.")
    #embedding = manifold.MDS(n_components=n)
    #X = embedding.fit_transform(X)
    return compute_all_kmeans(X, T, k, s, labels, verbose)


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

def ecc_kmeans(X, T, k, s, labels, verbose=True):
    ### Error Correcting Code approach
    n = X.shape[0]
    tic = time.time()
    np.random.seed(int(time.time()))
    random_subsets = np.random.binomial(1, s, (n, T))
    parity_bits = np.mod(np.matmul(X, random_subsets), 2)
    reduced_data = np.hstack([X, parity_bits])
    subtime = time.time() - tic
    kmeans_clusters_alg, conf_mat = correct_label_assignment(kmeans(reduced_data, k), labels)
    acc_alg = metrics.classification.accuracy_score(labels, kmeans_clusters_alg)
    time_alg = time.time() - tic
    print("ALG took %.3s seconds. Accuracy=%s" % (time_alg, acc_alg))
    if verbose:
        print(metrics.classification.classification_report(labels, kmeans_clusters_alg))
        print(metrics.confusion_matrix(labels, kmeans_clusters_alg))
    return reduced_data, acc_alg, time_alg, subtime


def ecc_kmeans_books(X, T, k, s, verbose=True):
    ### Error Correcting Code approach
    n = X.shape[0]
    tic = time.time()
    np.random.seed(int(time.time()))
    random_subsets = np.random.binomial(1, s, (n, T))
    parity_bits = np.mod(np.matmul(X, random_subsets), 2)
    reduced_data = np.hstack([X, parity_bits])
    subtime = time.time() - tic
    kmeans_clusters_alg = kmeans(reduced_data, k)
    
    time_alg = time.time() - tic
    print("ALG took %.3s seconds. Accuracy=%s" % (time_alg, acc_alg))
    return kmeans_clusters_alg


def compute_all_kmeans(X, T, k, s, labels, verbose=True):
    """
    :param X: array shape=(n_samples, n_features)
    :param T: ECC code length
    :param k: for k-means
    :param labels: ground truth cluster ids
    :param verbose: print details
    :return: acc_alg, acc_pca, acc_vanilla
    """
    n = X.shape[0]
    #BCHCode.decode()

    ### Error Correcting Code approach
    reduced_data, acc_alg, time_alg, subtime = ecc_kmeans(X, T, k, s, labels, verbose)

    ### Classic PCA approach
    tic = time.time()
    reduced_data2 = PCA().fit_transform(X)
    kmeans_clusters_standard, conf_mat2 = correct_label_assignment(kmeans(reduced_data2, k), labels)
    acc_pca = metrics.classification.accuracy_score(labels, kmeans_clusters_standard)
    time_pca = time.time() - tic
    print("PCA (%s components) took %.3s seconds. Accuracy=%s" % (n, time_pca, acc_pca))
    if verbose:
        print(metrics.classification.classification_report(labels, kmeans_clusters_standard))
        print(metrics.confusion_matrix(labels, kmeans_clusters_standard))
        plt.subplot(1, 2, 1)
        tmp = distance.squareform(distance.pdist(X))
        np.fill_diagonal(tmp, np.mean(tmp))
        plt.imshow(tmp)
        plt.subplot(1, 2, 2)
        tmp = distance.squareform(distance.pdist(reduced_data))
        np.fill_diagonal(tmp, np.mean(tmp))
        plt.imshow(tmp)

    ### ECC-PCA approach
    tic = time.time()
    reduced_data3 = PCA().fit_transform(reduced_data)
    kmeans_clusters_eccpca, conf_mat3 = correct_label_assignment(kmeans(reduced_data3, k), labels)
    acc_eccpca = metrics.classification.accuracy_score(labels, kmeans_clusters_eccpca)
    time_eccpca = time.time() - tic + subtime
    print("ECC-PCA (%s components) took %.3s seconds. Accuracy=%s" % (n, time_eccpca, acc_eccpca))
    if verbose:
        print(metrics.classification.classification_report(labels, kmeans_clusters_eccpca))
        print(metrics.confusion_matrix(labels, kmeans_clusters_eccpca))

    ### Vanilla k-means approach
    tic = time.time()
    reduced_data3 = X
    kmeans_clusters_vanilla, conf_mat3 = correct_label_assignment(kmeans(reduced_data3, k), labels)
    acc_vanilla = metrics.classification.accuracy_score(labels, kmeans_clusters_vanilla)
    time_vanilla = time.time() - tic
    print("Vanilla k-means took %.3s seconds. Accuracy=%s" % (time_vanilla, acc_vanilla))
    if verbose:
        print(metrics.classification.classification_report(labels, kmeans_clusters_vanilla))
        print(metrics.confusion_matrix(labels, kmeans_clusters_vanilla))

    return acc_alg, acc_pca, acc_eccpca, acc_vanilla, time_alg, time_pca, time_eccpca, time_vanilla


def subsampled_kmeans(X, k, percent):
    """ runs kmeans on subsampled adj matrix,
    :param X: currently expecting an n X n matrix (e.g. adj. matrix)
    :param k:
    :param percent:
    :return:
    """
    n = X.shape[0]
    smpl = int(n*percent)
    smplindices = np.random.randint(0, n, smpl)
    km = KMeans(init='k-means++', n_clusters=k, n_init=10)
    km.fit(X[np.ix_(smplindices, smplindices)])
    return km, smplindices


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
    runs = 20
    #p = 1 / 10  # log(n)/sqrt(n)
    #q = 1 / 200  # log(n)/(10*sqrt(n))
    p, q = 0.01, 0.003
    # p, q = 0.01, 0.003
    s = 0.5#sample size
    T = 5# int(n*(n-1)/2)
    res = list()
    timeres = list()
    for step in range(runs):
        print('iter #%s' % step)
        iterout = binarylimitsspecial(n, 4, T, p, q, s, runs < 5)
        res.append(iterout[:4])
        timeres.append(iterout[4:])
    res = np.asarray(res)
    timeres = np.asarray(timeres)
    plt.subplot(2, 1, 1)
    plt.boxplot(res, notch=True, labels=['', '', '', ''])
    plt.ylabel('Clustering accuracy')
    anovap = stats.f_oneway(*res.transpose())
    plt.title(('Comparing %s runs at n=%s'+'\n'+'p=%s q=%s T=%s s=%s'+'\n'+'p-value(anova)=%.2E') % (runs, n, p, q, T, s, anovap.pvalue))
    plt.subplot(2, 1, 2)
    plt.boxplot(timeres, notch=True, labels=['ALG', 'PCA', 'ECC-PCA', 'VANILLA'])
    plt.ylabel('Runtime(sec)')
    plt.savefig('results_%s_%s_%s_%s.png' % (n, p, q, T))
    plt.show()

def condition_on_T(n):
    runs = 20
    p, q = 0.01, 0.003
    s = 0.5
    T = [1, 5, 10, 20, 30, 40, 50, 80, 100, 150, 200]# int(n*(n-1)/2)
    res = list()
    for t in T:
        subres = list()
        for step in range(runs):
            print('T=%s iter #%s' % (t, step))
            X, labels = generate_block_stochastic_data(n, 4, p, q)
            _, acc_alg, _, _ = ecc_kmeans(X, t, 4, s, labels, False)
            subres.append(acc_alg)
        res.append(np.asarray(subres))
    res = np.asarray(res)
    errs = np.std(res, axis=1)
    means = np.mean(res, axis=1)
    plt.errorbar(T, means, yerr=errs)
    plt.ylabel('Clustering accuracy')
    plt.xlabel('ECC code size')
    plt.title(('ECC accuracy on %s runs at n=%s'+'\n'+'p=%s q=%s s=%s') % (runs, n, p, q, s))
    plt.savefig('results_conditioned_onT_%s_%s_%s.png' % (n, p, q))
    plt.show()

def save_clusters(t, clusters, books, inv_mapping,
                  filename = "tmp_clusters"):
    f = open(filename+str(t), "w")
    sets = {}
    for p in range(len(clusters)):
        if inv_mapping[clusters[p]] not in books: continue
        if clusters[p] not in sets:
            sets[clusters[p]] = []
        sets[clusters[p]].append(p)

    for c in sets:
        f.write("\n\nCluster "+str(c)+"\n")
        for p in sets[c]:
            f.write(inv_mapping[p]+" ")
            for x in books[inv_mapping[p]]:
                f.write(x+" ")
            f.write("\n")
        f.write("\n\n")
    f.close()

    
#####
## BX has no ground truth
#####
def condition_on_T_BX():
    runs = 20
    p, q = 0.01, 0.003
    s = 0.5
    T = [1, 5, 10, 20, 30, 40, 50, 80, 100, 150, 200]# int(n*(n-1)/2)
    X, mapping, inv_mapping, books = BX.Wrapper()
    res = list()
    for t in T:
        subres = list()
        for step in range(runs):
            print('T=%s iter #%s' % (t, step))
            # X, labels = generate_block_stochastic_data(n, 4, p, q)
            clust_alg = ecc_kmeans_books(X, t, 4, s, False)
            save_clusters(t, clust_alg, books, inv_mapping)
        #     subres.append(acc_alg)
        # res.append(np.asarray(subres))
    # res = np.asarray(res)
    # errs = np.std(res, axis=1)
    # means = np.mean(res, axis=1)
    # plt.errorbar(T, means, yerr=errs)
    # plt.ylabel('Clustering accuracy')
    # plt.xlabel('ECC code size')
    # plt.title(('ECC accuracy on %s runs at n=%s'+'\n'+'p=%s q=%s s=%s') % (runs, n, p, q, s))
    # plt.savefig('results_conditioned_onT_%s_%s_%s.png' % (n, p, q))
    # plt.show()


def condition_on_T_mush(n):
    runs = 20
    p, q = 0.01, 0.003
    s = 0.5
    T = [1, 5, 10, 20, 30, 40, 50, 80, 100] #, 150, 200]# int(n*(n-1)/2)
    X, labels = mush.ReadMushrooms()
    res = list()
    for t in T:
        subres = list()
        for step in range(runs):
            print('T=%s iter #%s' % (t, step))
            _, acc_alg, _, _ = ecc_kmeans(X, t, 2, s, labels, False)
            subres.append(acc_alg)
        res.append(np.asarray(subres))
    res = np.asarray(res)
    errs = np.std(res, axis=1)
    means = np.mean(res, axis=1)
    plt.errorbar(T, means, yerr=errs)
    plt.ylabel('Clustering accuracy')
    plt.xlabel('ECC code size')
    plt.title(('ECC accuracy on %s runs at n=%s'+'\n'+'p=%s q=%s s=%s') % (runs, n, p, q, s))
    plt.savefig('results_conditioned_onT_%s_%s_%s.png' % (n, p, q))
    plt.show()


def kmeans_subsample_density_estimator(n=1000, k=4, p=0.08, q=0.003, sample_ratio=0.2):
    print('n = %d k = %d sample_ratio = %.3f p = %.3f q=%.3f' % (n, k, sample_ratio, p, q))
    X, labels = generate_block_stochastic_data(n, k, p, q)
    km, idx = subsampled_kmeans(X, k, sample_ratio)
    clustidx = [np.where(km.labels_ == i)[0] for i in range(k)]
    sub_X = X[np.ix_(idx, idx)]
    sub_n = len(idx)
    intra_clust_sums = [np.sum(sub_X[np.ix_(tidx, tidx)]) for tidx in clustidx]
    p_hat = np.mean([intra_clust_sums[i]/(len(tidx)**2) for i, tidx in enumerate(clustidx)])
    q_hat = np.mean([(np.sum(sub_X[tidx, :]) - intra_clust_sums[i]) / (len(tidx)*(sub_n - len(tidx))) for i, tidx in enumerate(clustidx)])
    kmeans_clusters_alg, conf_mat = correct_label_assignment(km.labels_, labels[idx])
    acc_alg = metrics.classification.accuracy_score(labels[idx], kmeans_clusters_alg)
    total_mse = 0.5 * np.sqrt((p-p_hat)**2 + (q-q_hat)**2)
    print('subsampled Kmeans accuracy = %.3f p_hat = %.3f q_hat=%.3f totalMSE=%.3f' % (acc_alg, p_hat, q_hat, total_mse))

### SBM
kmeans_subsample_density_estimator()
#condition_on_T(600)
#wrapper(600)

### Digits
# digits()
