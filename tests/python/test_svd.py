import taichi as ti
import numpy as np
from pytest import approx


# https://www.seas.upenn.edu/~cffjiang/research/svd/svd.pdf
@ti.func
def svd2d(A, dt):
  R, S = ti.polar_decompose(A)
  c, s = 0.0, 0.0
  s1, s2 = 0.0, 0.0
  if S[0, 1] == 0:
    c, s = 1, 0
    s1, s2 = S[0, 0], S[1, 1]
  else:
    tao = 0.5 * (S[0, 0] - S[1, 1])
    w = ti.sqrt(tao ** 2 + S[0, 1] ** 2)
    t = 0.0
    if tao > 0:
      t = S[0, 1] / (tao + w)
    else:
      t = S[0, 1] / (tao - w)
    c = 1 / ti.sqrt(t ** 2 + 1)
    s = -t * c
    s1 = c ** 2 * S[0, 0] - 2 * c * s * S[0, 1] + s ** 2 * S[1, 1]
    s2 = s ** 2 * S[0, 0] + 2 * c * s * S[0, 1] + c ** 2 * S[1, 1]
  V = ti.Matrix.zero(dt, 2, 2)
  if s1 < s2:
    s1, s2 = s2, s1
    V = [[-s, c], [-c, -s]]
  else:
    V = [[c, s], [-s, c]]
  U = R @ V
  return U, ti.Matrix([[s1, ti.cast(0, dt)], [ti.cast(0, dt), s2]]), V
  


def svd3d(A, dt, iters=None):
  assert A.n == 3 and A.m == 3
  inputs = tuple([e.ptr for e in A.entries])
  assert dt in [ti.f32, ti.f64]
  if iters is None:
    if dt == ti.f32:
      iters = 5
    else:
      iters = 8
  if dt == ti.f32:
    rets = ti.core.sifakis_svd_f32(*inputs, iters)
  else:
    rets = ti.core.sifakis_svd_f64(*inputs, iters)
  assert len(rets) == 21
  U_entries = rets[:9]
  V_entries = rets[9:18]
  sig_entries = rets[18:]
  U = ti.expr_init(ti.Matrix.zero(dt, 3, 3))
  V = ti.expr_init(ti.Matrix.zero(dt, 3, 3))
  sigma = ti.expr_init(ti.Matrix.zero(dt, 3, 3))
  for i in range(3):
    for j in range(3):
      U(i, j).assign(U_entries[i * 3 + j])
      V(i, j).assign(V_entries[i * 3 + j])
    sigma(i, i).assign(sig_entries[i])
  return U, sigma, V

def mat_equal(A, B, tol=1e-6):
  return np.max(np.abs(A - B)) < tol


#@ti.func
def svd(A, dt):
  if (A.n == 2):
    return svd2d(A, dt)
  elif (A.n == 3):
    return svd3d(A, dt)
  else:
    raise Exception("SVD only supports 2D and 3D matrices")

@ti.all_archs
def _test_svd(n, dt):
  ti.get_runtime().set_default_fp(dt)
  
  A = ti.Matrix(n, n, dt=dt, shape=())
  A_reconstructed = ti.Matrix(n, n, dt=dt, shape=())
  U = ti.Matrix(n, n, dt=dt, shape=())
  UtU = ti.Matrix(n, n, dt=dt, shape=())
  sigma = ti.Matrix(n, n, dt=dt, shape=())
  V = ti.Matrix(n, n, dt=dt, shape=())
  VtV = ti.Matrix(n, n, dt=dt, shape=())
  
  @ti.kernel
  def run():
    for i in range(1):
      U[None], sigma[None], V[None] = svd(A[None], dt)
      UtU[None] = ti.transposed(U[None]) @ U[None]
      VtV[None] = ti.transposed(V[None]) @ V[None]
      A_reconstructed[None] = U[None] @ sigma[None] @ ti.transposed(V[None])
    
  if n == 3:
    A[None] = [[1, 1, 3], [9, -3, 2], [-3, 4, 2]]
  else:
    A[None] = [[1, 1], [9, -3]]
  
  run()
  
  assert mat_equal(UtU.to_numpy(), np.eye(n))
  assert mat_equal(VtV.to_numpy(), np.eye(n))
  assert mat_equal(A_reconstructed.to_numpy(), A.to_numpy(), tol=1e-5 if dt == ti.f32 else 1e-12)
  for i in range(n):
    for j in range(n):
      if i != j:
        assert sigma[None][i, j] == approx(0)
        
def test_svd():
  _test_svd(3, ti.f32)
  _test_svd(3, ti.f64)


@ti.all_archs
def test_transpose_no_loop():
  # TODO: fix this
  return
  A = ti.Matrix(3, 3, dt=ti.f32, shape=())
  U = ti.Matrix(3, 3, dt=ti.f32, shape=())
  sigma = ti.Matrix(3, 3, dt=ti.f32, shape=())
  V = ti.Matrix(3, 3, dt=ti.f32, shape=())
  
  @ti.kernel
  def run():
    U[None], sigma[None], V[None] = svd(A[None])
  
  run()
