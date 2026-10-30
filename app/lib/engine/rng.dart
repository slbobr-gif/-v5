// Детерминированные случайности. Совпадают бит в бит с tools/sim/engine.py.

/// 32-битный LCG.
class Rng {
  Rng(int state) : state = state & 0xFFFFFFFF;

  int state;

  int nextU32() {
    state = (state * 1664525 + 1013904223) & 0xFFFFFFFF;
    return state;
  }

  double nextFloat() => nextU32() / 4294967296.0;

  int pickWeighted(List<int> weights) {
    var total = 0;
    for (final w in weights) {
      total += w;
    }
    final r = nextU32() % total;
    var acc = 0;
    for (var i = 0; i < weights.length; i++) {
      acc += weights[i];
      if (r < acc) return i;
    }
    return weights.length - 1;
  }
}

/// FNV-1a по 32-битным словам (little-endian). Для погоды — не трогает основной RNG.
int hash32(List<int> parts) {
  var h = 2166136261;
  for (final p in parts) {
    final v = p & 0xFFFFFFFF;
    for (var shift = 0; shift < 32; shift += 8) {
      final byte = (v >> shift) & 0xFF;
      h = ((h ^ byte) * 16777619) & 0xFFFFFFFF;
    }
  }
  return h;
}
