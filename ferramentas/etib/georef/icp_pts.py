# -*- coding: utf-8 -*-
"""Ajuste rígido 2D (rotação + translação, sem escala) entre duas nuvens de pontos por ICP com chute inicial.
Funções usadas pelos scripts de georreferenciamento."""
import numpy as np, math


class Grade:
    """Vizinho mais próximo por grade (sem scipy), vetorizado por célula. Exato para distâncias ≤ cel."""
    def __init__(self, B, cel=1.0):
        self.B = np.asarray(B, float)[:, :2]; self.cel = float(cel)
        k = np.floor(self.B / self.cel).astype(np.int64)
        ordem = np.lexsort((k[:, 1], k[:, 0])); ks = k[ordem]
        mud = np.r_[True, np.any(ks[1:] != ks[:-1], axis=1)]
        ini = np.flatnonzero(mud); fim = np.r_[ini[1:], len(ks)]
        self.g = {(int(ks[a, 0]), int(ks[a, 1])): ordem[a:b] for a, b in zip(ini, fim)}
    def query(self, P):
        P = np.atleast_2d(np.asarray(P, float))[:, :2]
        dist = np.full(len(P), np.inf); idx = np.full(len(P), -1, dtype=np.int64)
        k = np.floor(P / self.cel).astype(np.int64)
        uk, inv = np.unique(k, axis=0, return_inverse=True)
        inv = inv.ravel(); ordem = np.argsort(inv, kind='stable')
        cortes = np.searchsorted(inv[ordem], np.arange(len(uk) + 1))
        for u in range(len(uk)):
            q = ordem[cortes[u]:cortes[u + 1]]
            gx, gy = int(uk[u, 0]), int(uk[u, 1])
            c = [self.g[(gx + dx, gy + dy)] for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (gx + dx, gy + dy) in self.g]
            if not c: continue
            c = np.concatenate(c)
            D = np.hypot(P[q, 0, None] - self.B[None, c, 0], P[q, 1, None] - self.B[None, c, 1])
            a = D.argmin(1)
            dist[q] = D[np.arange(len(q)), a]; idx[q] = c[a]
        return dist, idx

def rigid(A, B):
    ca, cb = A.mean(0), B.mean(0)
    H = (A - ca).T @ (B - cb)
    U, S, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[1] *= -1; R = Vt.T @ U.T
    return R, cb - R @ ca

def icp(A, B, R=None, t=None, tol=(2.0, 0.5, 0.1, 0.02, 0.005), it=8):
    """A (disc) -> B (base). Devolve R, t, pares (iA, iB) e resíduos do último passo."""
    if R is None: R = np.eye(2)
    if t is None: t = B.mean(0) - A.mean(0)
    for d in tol:
        tree = Grade(B, max(d, 0.5))
        for _ in range(it):
            P = A @ R.T + t
            dist, j = tree.query(P)
            m = dist < d
            if m.sum() < 3: break
            R, t = rigid(A[m], B[j[m]])
    P = A @ R.T + t
    dist, j = Grade(B, max(tol[-1], 0.5)).query(P)
    m = dist < tol[-1]
    return R, t, np.where(m)[0], j[m], dist[m]

def ang(R): return math.degrees(math.atan2(R[1, 0], R[0, 0]))
