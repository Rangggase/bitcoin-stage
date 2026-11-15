"""Tahap 1: blok, hash SHA-256, dan proof of work (hanya library standar)."""
import hashlib
import json
import sys
import time

DIFFICULTY = 4


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Block:
    def __init__(self, index, data, previous_hash, timestamp=None, nonce=0):
        self.index = index
        self.timestamp = time.time() if timestamp is None else timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        isi = json.dumps(
            {
                "index": self.index,
                "timestamp": self.timestamp,
                "data": self.data,
                "previous_hash": self.previous_hash,
                "nonce": self.nonce,
            },
            sort_keys=True,
        )
        return sha256_hex(isi)

    def mine(self, difficulty: int) -> int:
        """Cari nonce sampai hash diawali `difficulty` nol. Mengembalikan jumlah percobaan."""
        target = "0" * difficulty
        self.nonce = 0
        self.hash = self.compute_hash()
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.compute_hash()
        return self.nonce + 1


class Blockchain:
    def __init__(self, difficulty: int = DIFFICULTY):
        self.difficulty = difficulty
        genesis = Block(0, "Genesis Block", "0" * 64, timestamp=0)
        genesis.mine(difficulty)
        self.chain = [genesis]

    def add_block(self, data) -> Block:
        last = self.chain[-1]
        block = Block(last.index + 1, data, last.hash)
        block.mine(self.difficulty)
        self.chain.append(block)
        return block

    def is_valid(self) -> bool:
        target = "0" * self.difficulty
        for i, block in enumerate(self.chain):
            if block.hash != block.compute_hash():
                return False  # isi diubah tanpa mining ulang
            if not block.hash.startswith(target):
                return False  # tidak memenuhi difficulty
            if i > 0 and block.previous_hash != self.chain[i - 1].hash:
                return False  # sambungan rantai putus
        return True

    def print_chain(self, file=None) -> None:
        """Cetak rantai dalam bentuk tabel teks."""
        out = file or sys.stdout
        header = f"{'Idx':<4}{'Nonce':<9}{'Data':<22}{'Prev hash':<14}{'Hash':<14}"
        print(header, file=out)
        print("-" * len(header), file=out)
        for b in self.chain:
            data = str(b.data)
            data = data if len(data) <= 20 else data[:18] + ".."
            print(
                f"{b.index:<4}{b.nonce:<9}{data:<22}{b.previous_hash[:12]:<14}{b.hash[:12]:<14}",
                file=out,
            )


if __name__ == "__main__":
    diff = int(sys.argv[1]) if len(sys.argv) > 1 else DIFFICULTY
    bc = Blockchain(diff)
    for d in ("Alice kirim 1 BTC ke Bob", "Bob kirim 0.5 BTC ke Carol"):
        t0 = time.perf_counter()
        blk = bc.add_block(d)
        print(f"Blok {blk.index} ditambang: nonce={blk.nonce}, hash={blk.hash[:16]}..., {time.perf_counter() - t0:.2f} dtk")
    bc.print_chain()
    print("Valid awalnya?  ", bc.is_valid())
    bc.chain[1].data = "Alice kirim 100 BTC ke Mallory"
    print("Valid setelah data blok 1 diubah?", bc.is_valid())
