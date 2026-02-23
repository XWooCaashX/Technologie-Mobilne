import math
import time
import matplotlib.pyplot as plt

class MojGenerator:
    def __init__(self, ziarno=None):
        self.m = 2**31 - 1
        self.a = 16807
        self.stan = int(time.time()) % self.m if ziarno is None else ziarno

    def losuj_u(self):
        self.stan = (self.a * self.stan) % self.m
        return self.stan / self.m

def gen_poissona(gen, lam):
    x, s, q = -1, 1.0, math.exp(-lam)
    while s > q:
        s *= gen.losuj_u()
        x += 1
    return x

def gen_normalny(gen, mu, sigma):
    u1, u2 = gen.losuj_u(), gen.losuj_u()
    z0 = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
    return mu + z0 * sigma

def uruchom():
    n, lam, mu, sigma, ziarno = 10000, 4.0, 0.0, 1.0, 42
    
    gen_p = MojGenerator(ziarno)
    gen_n = MojGenerator(ziarno)

    dane_p = [gen_poissona(gen_p, lam) for _ in range(n)]
    dane_n = [gen_normalny(gen_n, mu, sigma) for _ in range(n)]

    plt.figure(figsize=(12, 6))

    plt.subplot(1, 2, 1)
    plt.hist(dane_p, bins=range(min(dane_p), max(dane_p) + 2), density=True, alpha=0.7, color='blue', edgecolor='black')
    plt.title(f"Rozklad Poissona (lambda={lam})")

    plt.subplot(1, 2, 2)
    plt.hist(dane_n, bins=50, density=True, alpha=0.7, color='green', edgecolor='black')
    plt.title(f"Rozklad Normalny (mu={mu}, sigma={sigma})")

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    uruchom()