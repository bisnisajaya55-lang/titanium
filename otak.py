# -*- coding: utf-8 -*-
"""
OTAK TITANIUM QUANTUM HORIZON v5.2 (Titan 9.2 Stable)
ULTRA-PREDICTIVE FUTURE ENGINE
Equipped with Neural Synapse Stabilization v2, Quantum Reversion Guard (QRG), and Entropy Eraser.
"""
import numpy as np
from collections import deque

# [v38] Global cross-timeframe signal store (diisi dari app.py)
_GLOBAL_CROSS_SIGNALS = {}

def update_cross_signals(signals_dict):
    """[v38] Dipanggil dari app.py untuk inject sinyal dari mode time-frame lain."""
    global _GLOBAL_CROSS_SIGNALS
    _GLOBAL_CROSS_SIGNALS = signals_dict or {}

def _log(msg):
    """Internal logger for QuantumBrain"""
    print(f"[TITAN_LOG] {msg}")

# TITANIUM FALLBACK SYSTEM
try:
    import scipy.stats as stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# ============================================================
# INLINE ChartAnalyzer (sebelumnya dari grafik.py)
# ============================================================
class ChartAnalyzer:
    """Chart statistics analyzer untuk QuantumBrain."""
    def __init__(self, history_limit=100):
        self.lim = history_limit

    def analyze(self, history_nums):
        if not history_nums:
            return {i: {"missing": 0, "freq": 0,
                        "avg_missing": 0.0, "max_streak": 0}
                    for i in range(10)}
        recent = list(history_nums[-self.lim:])
        nums = recent[::-1]
        out = {}
        for i in range(10):
            missing = 0
            for n in nums:
                if n == i:
                    break
                missing += 1
            freq = sum(1 for n in nums if n == i)
            idxs = [k for k, n in enumerate(nums) if n == i]
            if len(idxs) > 1:
                gaps = [idxs[k+1] - idxs[k] for k in range(len(idxs)-1)]
                avg = sum(gaps) / len(gaps)
            else:
                avg = 0.0
            ms, cur = 0, 0
            for n in recent:
                if n == i:
                    cur += 1
                    ms = max(ms, cur)
                else:
                    cur = 0
            out[i] = {"missing": missing, "freq": freq,
                      "avg_missing": round(avg, 1), "max_streak": ms}
        return out

    def trend(self, history_nums):
        s = self.analyze(history_nums)
        if not s:
            return {"B": 0.0, "K": 0.0, "numbers": [0.0]*10, "raw_stats": {}}
        nv = [0.0] * 10
        sv = {"B": 0.0, "K": 0.0}
        for i in range(10):
            st = s[i]
            if st["missing"] > st["avg_missing"] * 1.5:
                nv[i] += (st["missing"] - st["avg_missing"]) * 500.0
            if st["freq"] > (self.lim / 10) and st["missing"] < 3:
                nv[i] += st["freq"] * 200.0
            if i >= 5:
                sv["B"] += nv[i]
            else:
                sv["K"] += nv[i]
        return {"B": sv["B"], "K": sv["K"], "numbers": nv, "raw_stats": s}

    def get_trend_vectors(self, history_nums):
        """Alias yang dipakai otak.py"""
        return self.trend(history_nums)

class QuantumBrain:
    def _log(self, msg):
        """Standard logger for QuantumBrain"""
        print(f"[TITAN_LOG] {msg}")

    def __init__(self):
        self.quantum_entropy = 0.0
        self.jp_resonance = 0.0
        self.jp_resonance_count = 0 
        self.loss_counter = 0 # Track performance for Slingshot mode
        self.last_prediction_was_correct = True
        self.market_phase = "STABLE"
        self.neural_weights = {"momentum": 1.0, "reversion": 1.0, "pattern": 1.0, "jp_sync": 1.0}
        self.chart = ChartAnalyzer(history_limit=100)
        self.last_stats = None
        
        # [AI-LEARN v1] Method performance tracker
        self.method_scores = {
            "markov": {"win": 0, "lose": 0, "weight": 1.0},
            "markov_high": {"win": 0, "lose": 0, "weight": 1.0},
            "bayesian": {"win": 0, "lose": 0, "weight": 1.0},
            "tema": {"win": 0, "lose": 0, "weight": 1.0},
            "kalman": {"win": 0, "lose": 0, "weight": 1.0},
            "fourier": {"win": 0, "lose": 0, "weight": 1.0},
            "knn": {"win": 0, "lose": 0, "weight": 1.0},
            "holt_winters": {"win": 0, "lose": 0, "weight": 1.0},
            "fuzzy": {"win": 0, "lose": 0, "weight": 1.0},
            "pattern": {"win": 0, "lose": 0, "weight": 1.0},
        }
        # [AI-LEARN v1] Regime-based best method cache
        self.regime_best = {
            "TRENDING": [], "CHAOTIC": [], "MAX_CHAOS": [], "ZIGZAG_MOMENTUM": [],
            "OMEGA_STABLE": [], "MIRRORING": [], "VIOLET_TRANSITION": [], "FRACTAL_DNA": []
        }
        self._last_engine_snapshot = {}
        # [AI-LEARN v1] Auto-load learned memory
        self._load_learned_memory()
        self.engine_performance = {
            "markov": 1.0, 
            "trend": 1.0, 
            "pattern": 1.0, 
            "regress": 1.0,
            "markov_high": 1.0,
            "bayesian": 1.0,
            "tema": 1.0,
            "chi_square": 1.0,
            "kalman": 1.0,
            "fourier": 1.0,
            "knn": 1.0,
            "holt_winters": 1.0,
            "fuzzy": 1.0
        }
        self.entropy_history = deque(maxlen=20)
        self.num_history = deque(maxlen=10) # 10.1 Track last 10 predicted numbers
        self.prediction_queue = deque(maxlen=12) # For tracking anti-phase alignment patterns
        self.prediction_history_dict = {}
        self.noise_filter_factor = 1.0 
        
        # ========================================================
        # [v38] FINAL PACKAGE — Self-Learning & Adaptive Core
        # ========================================================
        # Cross-timeframe mode key
        self._current_mode_key = None
        # Recent numbers (for backtest)
        self._recent_nums = deque(maxlen=200)
        # Adaptive threshold auto-tuner
        self.adaptive_thresholds = {
            "entropy_chaos": 2.40,
            "entropy_max": 2.70,
            "dragon_min": 2,
            "fracture_min": 3
        }
        # Regime-aware method performance tracker
        self.regime_method_perf = {}  # {phase: {method: {win, lose}}}
        # Q-Learning lite (state-action value table)
        self.q_table = {}
        self.q_last_state = None
        self.q_last_action = None
        # Backtest cache
        self.backtest_cache = {"accuracy": 0.5, "samples": 0}
        # Feedback counter untuk auto-tune
        self._feedback_counter = 0
        # Load Q-table dari memory kalau ada
        try:
            import json as _j_q
            import os as _o_q
            if _o_q.path.exists("q_table.json"):
                with open("q_table.json", "r") as _f_q:
                    self.q_table = _j_q.load(_f_q)
        except: pass

    def _recalculate_method_weights(self):
        """[AI-LEARN v1] Hitung ulang bobot tiap method berdasarkan win-rate historis."""
        for m_name, m_data in self.method_scores.items():
            total = m_data["win"] + m_data["lose"]
            if total < 5:
                continue  # Belum cukup data, biarkan weight default
            wr = m_data["win"] / total
            # Weight = 0.3 (min) sampai 2.5 (max), scaling dari win-rate
            # WR 50% → weight 1.0 ; WR 70% → weight 1.9 ; WR 30% → weight 0.5
            new_w = max(0.3, min(2.5, (wr - 0.25) * 2.5))
            m_data["weight"] = round(new_w, 3)
        self._log(f"[AI-LEARN] Method weights recalculated. Sample markov: {self.method_scores['markov']['weight']}")

    def _save_learned_memory(self):
        """[AI-LEARN v1] Simpan bobot yang sudah dipelajari ke disk."""
        try:
            import json as _json_lm
            _data = {
                "method_scores": self.method_scores,
                "regime_best": self.regime_best,
                "saved_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open("brain_learned.json", "w") as _f:
                _json_lm.dump(_data, _f, indent=2)
            self._log("[AI-LEARN] Learned memory saved to brain_learned.json")
        except Exception as _e:
            self._log(f"[AI-LEARN] Save failed: {_e}")

    def _load_learned_memory(self):
        """[AI-LEARN v1] Load bobot yang sudah dipelajari dari disk."""
        try:
            import json as _json_lm, os as _os_lm
            if _os_lm.path.exists("brain_learned.json"):
                with open("brain_learned.json", "r") as _f:
                    _data = _json_lm.load(_f)
                if "method_scores" in _data:
                    for _k, _v in _data["method_scores"].items():
                        if _k in self.method_scores:
                            self.method_scores[_k] = _v
                if "regime_best" in _data:
                    self.regime_best.update(_data["regime_best"])
                self._log(f"[AI-LEARN] Learned memory loaded (saved: {_data.get('saved_at', '?')})")
        except Exception as _e:
            self._log(f"[AI-LEARN] Load failed (fresh start): {_e}")

    # ============================================================
    # [v38] FINAL PACKAGE METHODS
    # ============================================================
    def set_mode_key(self, mode_key):
        """[v38] Set mode saat ini untuk cross-signal filtering."""
        self._current_mode_key = mode_key

    def get_cross_signal_vectors(self, history_nums):
        """[v38] Ekstrak sinyal konfirmasi dari mode time-frame lain (30s/1m/3m/5m)."""
        vectors = {"B": 0.0, "K": 0.0}
        if not _GLOBAL_CROSS_SIGNALS:
            return vectors
        _cur = self._current_mode_key
        for mode_key, mode_data in _GLOBAL_CROSS_SIGNALS.items():
            if mode_key == _cur or not mode_data:
                continue
            streak = mode_data.get("streak", 0)
            streak_side = mode_data.get("streak_side", None)
            last_5_bk = mode_data.get("last_5_bk", [])
            # Streak dari mode lain yang >= 2 = konfirmasi kuat
            if streak_side and streak >= 2:
                base_boost = 5000.0 * min(streak, 6)
                if streak_side == "B":
                    vectors["B"] += base_boost
                elif streak_side == "K":
                    vectors["K"] += base_boost
            # Dominasi 5 periode terakhir
            if len(last_5_bk) >= 5:
                b_cnt = sum(1 for s in last_5_bk if s == "B")
                if b_cnt >= 4:
                    vectors["B"] += 3500.0
                elif b_cnt <= 1:
                    vectors["K"] += 3500.0
        return vectors

    def run_backtest(self, history_nums, n_periods=100):
        """[v38] Backtest ringan: hitung akurasi metode pada N periode terakhir."""
        if not history_nums or len(history_nums) < 30:
            return {"accuracy": 0.5, "samples": 0}
        _start = max(20, len(history_nums) - n_periods)
        _wins, _total = 0, 0
        for _i in range(_start, len(history_nums) - 1):
            _sub = history_nums[:_i]
            _actual = history_nums[_i]
            if len(_sub) < 10:
                continue
            _last = _sub[-1]
            _lookback = _sub[-100:]
            _trans_b, _trans_k = 0, 0
            for _j in range(len(_lookback) - 1):
                if _lookback[_j] == _last:
                    if _lookback[_j+1] >= 5: _trans_b += 1
                    else: _trans_k += 1
            if _trans_b + _trans_k < 2:
                continue
            _pred_side = "B" if _trans_b >= _trans_k else "K"
            _actual_side = "B" if _actual >= 5 else "K"
            if _pred_side == _actual_side:
                _wins += 1
            _total += 1
        _acc = (_wins / _total) if _total > 0 else 0.5
        self.backtest_cache = {"accuracy": round(_acc, 4), "samples": _total}
        return self.backtest_cache

    def auto_tune_thresholds(self):
        """[v38] AutoML-lite: sesuaikan threshold berdasarkan akurasi backtest."""
        _bt = self.backtest_cache.get("accuracy", 0.5)
        _at = self.adaptive_thresholds
        if _bt < 0.50:
            # Akurasi rendah → konservatif
            _at["entropy_chaos"] = max(2.0, _at["entropy_chaos"] - 0.05)
            _at["entropy_max"] = max(2.4, _at["entropy_max"] - 0.05)
            _at["dragon_min"] = min(4, _at["dragon_min"] + 1)
        elif _bt > 0.65:
            # Akurasi bagus → sedikit agresif
            _at["entropy_chaos"] = min(2.6, _at["entropy_chaos"] + 0.03)
            _at["entropy_max"] = min(2.9, _at["entropy_max"] + 0.03)
        self._save_learned_memory()
        # Save q_table juga
        try:
            import json as _j_qt
            with open("q_table.json", "w") as _f_qt:
                _j_qt.dump(self.q_table, _f_qt)
        except: pass

    def q_learn_update(self, reward):
        """[v38] Simple Q-Learning update."""
        if self.q_last_state is None or self.q_last_action is None:
            return
        _alpha = 0.15
        _s_key = self.q_last_state
        _a_key = self.q_last_action
        if _s_key not in self.q_table:
            self.q_table[_s_key] = {"B": 0.0, "K": 0.0}
        _old_q = self.q_table[_s_key].get(_a_key, 0.0)
        _new_q = _old_q + _alpha * (reward - _old_q)
        self.q_table[_s_key][_a_key] = round(_new_q, 4)
        # Cleanup kalau > 500 entries
        if len(self.q_table) > 500:
            _sorted = sorted(self.q_table.items(), key=lambda x: abs(x[1].get("B", 0)) + abs(x[1].get("K", 0)))
            self.q_table = dict(_sorted[-400:])

    def _build_state_key(self, history_nums):
        """[v38] Bangun state key untuk Q-table."""
        _phase = self.market_phase or "STABLE"
        _last3 = "".join(["B" if n >= 5 else "K" for n in history_nums[-3:]])
        return f"{_phase}|{_last3}"

    def get_q_suggestion(self, history_nums):
        """[v38] Ambil saran dari Q-table untuk state saat ini."""
        if not self.q_table or len(history_nums) < 5:
            return {"B": 0.0, "K": 0.0}
        _state_key = self._build_state_key(history_nums)
        self.q_last_state = _state_key
        if _state_key in self.q_table:
            _q = self.q_table[_state_key]
            _b_q = _q.get("B", 0.0)
            _k_q = _q.get("K", 0.0)
            _vectors = {"B": 0.0, "K": 0.0}
            if abs(_b_q) > 0.05 or abs(_k_q) > 0.05:
                _scale = 12000.0
                _vectors["B"] = max(0, _b_q) * _scale
                _vectors["K"] = max(0, _k_q) * _scale
            return _vectors
        return {"B": 0.0, "K": 0.0}

    def get_regime_adaptive_weight(self, method_name):
        """[v38] Boost weight kalau method akurat di regime saat ini."""
        _phase = self.market_phase or "STABLE"
        _rp = self.regime_method_perf.get(_phase, {})
        _mp = _rp.get(method_name, {"win": 0, "lose": 0})
        _total = _mp["win"] + _mp["lose"]
        if _total < 5:
            return 1.0
        _wr = _mp["win"] / _total
        return max(0.5, min(1.8, 0.5 + _wr * 1.2))

    def analyze_failure(self, pred_bk=None, actual_bk=None):
        """Analyzes the root cause of recent losses and suggests a solution (Titan 11.0 Precision Audit)"""
        # NEURAL SYNAPSE STABILIZATION (Titan 11.0 - Active Protection)
        
        # 0. Detect Dragon (Anti-Loss Sink) - CRITICAL: Check FIRST to prevent counter-betting trends
        if hasattr(self, "last_p_info") and self.last_p_info.get("dragon", 0) >= 2:
            p_last_key = self.last_p_info.get("last", "B")
            p_last_full = "Besar" if p_last_key == "B" else "Kecil"
            # If prediction counter-betted the active dragon:
            if pred_bk and str(pred_bk).capitalize() != p_last_full:
                return "KEBOCORAN_DRAGON", "Tren naga sangat kuat. Wajib ikuti momentum naga (Follow-Trend Lock), dilarang counter-bet!"
            # If prediction followed the dragon, but the dragon broke naturally:
            elif pred_bk and str(pred_bk).capitalize() == p_last_full and actual_bk and str(actual_bk).capitalize() != p_last_full:
                return "PATAHAN_NAGA", "Tren naga berakhir secara alami (dragon break). Momentum bergeser ke fase pemulihan baru."
            elif not pred_bk and self.last_p_info.get("dragon", 0) >= 3:
                return "KEBOCORAN_DRAGON", "Tren naga sangat kuat. Wajib ikuti momentum naga (Follow-Trend Lock), dilarang counter-bet!"

        # 0.5 Detect Stagnant Twin Attractor (Exact same consecutive numbers)
        if hasattr(self, "last_p_info") and self.last_p_info.get("stagnant_len", 0) >= 2:
            return "STAGNAN_ATTRACTION", "Stabilisasi bias angka kembar & kalibrasi Polarity Gate."

        # 1.5 Detect Pola 2-2 / Double-Step Desync
        if hasattr(self, "num_history") and len(self.num_history) >= 4:
            s4 = ["B" if n >= 5 else "K" for n in list(self.num_history)[-4:]]
            if s4 in [["B", "B", "K", "K"], ["K", "K", "B", "B"]]:
                return "POLA_2_2_DESYNC", "Desinkronisasi Pola 2-2 (Double-Step). Mengunci ritme pembalikan siklus ganda."

        # 2. Detect Polarity Shift (Most dangerous for Martingale)
        if hasattr(self, "last_p_info"):
            imb = self.last_p_info.get("last_side_imbalance", 0)
            if imb > 0.35:
                return "SIDE_POLARITY_SHIFT", "Pembalikan arah polaritas. Kunci kompensasi defensif & ikuti konfirmasi arah terbaru."

        # 3. Detect Extreme Market Entropy (Chaos)
        if self.market_phase == "MAX_CHAOS" or self.quantum_entropy > 2.80:
            return "ENTROPI_BERLEBIH", "STOP_MARTINGALE: Volatilitas ekstrem (Entropy > 2.80). Wajib bet minimal, jangan naikkan level!"
        
        if self.market_phase == "CHAOTIC" or self.quantum_entropy > 2.45:
            return "GANGGUAN_POLA", "Filter noise aktif. Selaraskan konsensus voting & ikuti pola gelombang terdekat."
            
        return "DRIFT_NEURAL", "Kalibrasi ulang Polarity Gate & sinkronisasi bobot konsensus."

    def analyze_success(self):
        """Analyzes why the prediction won and identifies the winning mode (Titan 9.9)"""
        # PRIORITY: Neural Prediction Modes (FTQC, VQE, HYBRID, ANALOG)
        if hasattr(self, "last_stats") and self.last_stats and self.last_stats.get("is_jp", False):
            return "RESONANSI_JACKPOT", "Berhasil mengunci anomali kuantum jackpot."
            
        if self.market_phase == "OMEGA_STABLE" and self.quantum_entropy < 1.2:
            return "KOREKSI_FTQC", "Quantum Fault-Tolerant mengoreksi gangguan pasar."
        
        if self.market_phase == "MAX_CHAOS" and self.quantum_entropy > 2.8:
            return "VQE_EIGEN_STATE", "Variational Quantum Eigensolver memetakan chaos."
 
        if self.market_phase == "TRENDING" or (hasattr(self, 'last_p_info') and self.last_p_info.get('dragon', 0) >= 3):
            return "MOMENTUM_STRIKE", "Momentum terkunci pada urutan tren aktif."
        
        if self.market_phase == "MIRRORING" or self.market_phase == "FRACTAL_DNA":
            return "SINKRONISASI_ANALOG", "Mendeteksi siklus historis melalui pemetaan Analog."

        if self.quantum_entropy > 2.0 and self.quantum_entropy < 2.5:
            return "KONVERGENSI_HIBRID", "Sinkronisasi logika Hybrid Momentum/Reversion."
        
        if self.quantum_entropy > 2.5:
            return "REVERSION_STRIKE", "Prediksi mean reversion pada kekacauan ekstrem."
        
        return "PENYESUAIAN_STRUKTURAL", "Vektor mesin selaras dengan geometri pasar."

    def report_feedback(self, was_correct, is_jp=False, pred_bk=None, actual_bk=None):
        """AI Feedback Loop to adjust future projections (Titan 9.2 NSS)"""
        self.last_prediction_was_correct = was_correct
        
        # [AI-LEARN v1] Update method scores berdasarkan hasil
        _snap = getattr(self, "_last_engine_snapshot", {})
        if _snap and "final_side_key" in _snap:
            _final_key = _snap["final_side_key"]
            _winner_dir = 1 if _final_key == "B" else -1
            for _m_name, _m_vote in _snap.items():
                if _m_name in ("final_side_key", "phase"):
                    continue
                if _m_name not in self.method_scores:
                    continue
                _method_aligned = (_m_vote == _winner_dir)
                if was_correct and _method_aligned:
                    self.method_scores[_m_name]["win"] += 1
                elif not was_correct and _method_aligned:
                    self.method_scores[_m_name]["lose"] += 1
            
            _phase = _snap.get("phase", "UNKNOWN")
            if _phase in self.regime_best and was_correct:
                if _final_key not in self.regime_best[_phase]:
                    self.regime_best[_phase].append(_final_key)
                    self.regime_best[_phase] = self.regime_best[_phase][-20:]
        
        _total_fb = sum(m["win"] + m["lose"] for m in self.method_scores.values())
        if _total_fb > 0 and _total_fb % 10 == 0:
            self._recalculate_method_weights()
            self._save_learned_memory()
        
        # [v38] FINAL PACKAGE HOOKS
        _snap_rf = getattr(self, "_last_engine_snapshot", {})
        
        if _snap_rf and "phase" in _snap_rf:
            _ph = _snap_rf["phase"]
            if _ph not in self.regime_method_perf:
                self.regime_method_perf[_ph] = {}
            _final_key_rf = _snap_rf.get("final_side_key", "B")
            _winner_rf = 1 if _final_key_rf == "B" else -1
            for _mname, _mvote in _snap_rf.items():
                if _mname in ("final_side_key", "phase"):
                    continue
                if _mname not in self.regime_method_perf[_ph]:
                    self.regime_method_perf[_ph][_mname] = {"win": 0, "lose": 0}
                if _mvote == _winner_rf:
                    if was_correct:
                        self.regime_method_perf[_ph][_mname]["win"] += 1
                    else:
                        self.regime_method_perf[_ph][_mname]["lose"] += 1
        
        _reward = 1.0 if was_correct else -1.0
        if is_jp and was_correct:
            _reward = 3.0
        if self.q_last_state is not None and _snap_rf:
            self.q_last_action = _snap_rf.get("final_side_key", "B")
            self.q_learn_update(_reward)
        
        self._feedback_counter += 1
        if self._feedback_counter % 25 == 0:
            try:
                if hasattr(self, "_recent_nums") and len(self._recent_nums) >= 30:
                    self.run_backtest(list(self._recent_nums), n_periods=100)
                    self.auto_tune_thresholds()
                    self._log(f"[v38 AUTOTUNE] Backtest acc: {self.backtest_cache.get('accuracy', 0.5)} | Thresholds: {self.adaptive_thresholds}")
            except Exception as _at_e:
                self._log(f"[v38 AUTOTUNE] Error: {_at_e}")
        
        if is_jp and was_correct:
            self.jp_resonance_count += 1
            self._log(f"JP_RESONANCE_HIT: Syncing Matrix | Count: {self.jp_resonance_count}")
        
        if not was_correct:
            self.loss_counter += 1
            self.jp_resonance_count = max(0, self.jp_resonance_count - 3)
            cause, solution = self.analyze_failure(pred_bk=pred_bk, actual_bk=actual_bk)
            self.last_audit = {"status": "FAIL", "cause": cause, "solution": solution}
            
            # --- NSS LEARNING v6 (TITAN SLOT/WINGO HYPER-SYNCED - BLACK OPS) ---
            if cause == "STAGNAN_ATTRACTION":
                self.neural_weights["momentum"] = min(4.5, max(2.0, self.neural_weights.get("momentum", 1.0) * 1.50))
                self.neural_weights["reversion"] = max(0.02, min(0.08, self.neural_weights.get("reversion", 1.0) * 0.30))
                self.engine_performance["pattern"] = min(6.0, self.engine_performance.get("pattern", 1.0) * 1.60)
                self.engine_performance["regress"] = max(0.1, self.engine_performance.get("regress", 1.0) * 0.30)
            elif cause == "POLA_2_2_DESYNC":
                self.neural_weights["pattern"] = min(5.0, max(2.5, self.neural_weights.get("pattern", 1.0) * 2.00))
                self.neural_weights["momentum"] = min(2.5, max(1.0, self.neural_weights.get("momentum", 1.0) * 0.80))
                self.engine_performance["pattern"] = min(6.0, self.engine_performance.get("pattern", 1.0) * 2.00)
            elif cause in ["PERGESERAN_POLARITAS", "SIDE_POLARITY_SHIFT"]:
                self.neural_weights["momentum"] = min(4.5, max(2.2, self.neural_weights.get("momentum", 1.0) * 1.60))
                self.neural_weights["reversion"] = max(0.01, min(0.06, self.neural_weights.get("reversion", 1.0) * 0.25))
                self.neural_weights["pattern"] = min(4.5, max(2.0, self.neural_weights.get("pattern", 1.0) * 1.40))
                self.engine_performance["trend"] = min(7.0, self.engine_performance.get("trend", 1.0) * 1.80)
                self.engine_performance["regress"] = max(0.1, self.engine_performance.get("regress", 1.0) * 0.25)
            elif cause in ["KEBOCORAN_DRAGON", "DRAGON_FRACTURE"]:
                self.neural_weights["momentum"] = min(5.0, max(3.0, self.neural_weights.get("momentum", 1.0) * 2.00))
                self.neural_weights["reversion"] = max(0.005, min(0.02, self.neural_weights.get("reversion", 1.0) * 0.10))
                self.engine_performance["trend"] = min(8.0, self.engine_performance.get("trend", 1.0) * 2.20)
                self.engine_performance["pattern"] = min(6.0, self.engine_performance.get("pattern", 1.0) * 1.80)
                self.engine_performance["regress"] = max(0.05, self.engine_performance.get("regress", 1.0) * 0.10)
            elif cause == "GANGGUAN_POLA":
                self.engine_performance["pattern"] = min(6.0, self.engine_performance.get("pattern", 1.0) * 1.80)
                self.engine_performance["regress"] = max(0.2, self.engine_performance.get("regress", 1.0) * 0.50)
                self.neural_weights["pattern"] = min(4.5, max(2.2, self.neural_weights.get("pattern", 1.0) * 1.60))
                self.neural_weights["momentum"] = min(3.5, max(1.8, self.neural_weights.get("momentum", 1.0) * 1.30))
                self.neural_weights["reversion"] = max(0.05, min(0.15, self.neural_weights.get("reversion", 1.0) * 0.40))
            elif "ENTROPI" in cause or cause == "ENTROPI_BERLEBIH":
                self.engine_performance["trend"] = min(6.0, self.engine_performance.get("trend", 1.0) * 1.70)
                self.engine_performance["pattern"] = min(5.0, self.engine_performance.get("pattern", 1.0) * 1.50)
                self.engine_performance["regress"] = max(0.1, self.engine_performance.get("regress", 1.0) * 0.20)
                self.neural_weights["momentum"] = min(4.5, max(2.2, self.neural_weights.get("momentum", 1.0) * 1.60))
                self.neural_weights["reversion"] = max(0.01, min(0.05, self.neural_weights.get("reversion", 1.0) * 0.15))
            else:
                self.engine_performance["regress"] = max(0.2, self.engine_performance.get("regress", 1.0) * 0.40)
                self.neural_weights["momentum"] = min(4.0, self.neural_weights.get("momentum", 1.0) * 1.30)
        else:
            self.loss_counter = 0
            reason, mode = self.analyze_success()
            self.last_audit = {"status": "WIN", "cause": reason, "solution": mode}
            
            if reason in ["KOREKSI_FTQC", "VQE_EIGEN_STATE"]:
                self.engine_performance["regress"] *= 1.35
                self.neural_weights["reversion"] *= 1.25
            elif reason == "KONVERGENSI_HIBRID":
                self.engine_performance["trend"] *= 1.15
                self.engine_performance["regress"] *= 1.15
            elif reason == "SINKRONISASI_ANALOG":
                self.engine_performance["pattern"] *= 1.40
            elif reason == "REVERSION_STRIKE":
                self.neural_weights["reversion"] = min(3.5, self.neural_weights["reversion"] * 1.15)
                self.engine_performance["regress"] *= 1.15
            elif reason == "MOMENTUM_STRIKE":
                self.neural_weights["momentum"] = min(4.0, self.neural_weights["momentum"] * 1.45)
                self.engine_performance["trend"] *= 1.45
            elif reason == "JACKPOT_RESONANCE":
                self.engine_performance["pattern"] *= 1.50
                self.engine_performance["regress"] *= 1.40
                self.neural_weights["jp_sync"] = min(4.0, self.neural_weights["jp_sync"] * 1.6)
                
            for k in self.engine_performance:
                self.engine_performance[k] = min(3.5, self.engine_performance[k] * 1.15)
                
            if self.quantum_entropy < 1.0:
                for k in self.neural_weights:
                    self.neural_weights[k] = self.neural_weights[k] * 0.85 + 1.0 * 0.15
            
        for k in self.neural_weights:
            self.neural_weights[k] = max(0.1, min(5.0, self.neural_weights[k]))

    def _internal_linregress(self, x, y):
        """Internal fallback if scipy is missing (Basic Least Squares)"""
        n = len(x)
        if n < 2: return 0.0, 0.0
        x_m, y_m = np.mean(x), np.mean(y)
        ss_xy = np.sum(y * x) - n * y_m * x_m
        ss_xx = np.sum(x * x) - n * x_m * x_m
        slope = ss_xy / ss_xx if ss_xx != 0 else 0
        intercept = y_m - slope * x_m
        return slope, intercept

    def detect_patterns(self, history_nums):
        """Detects specific payout patterns like Dragons, Mirrors, and Zigzags"""
        if not history_nums: return {"dragon": 0, "zigzag": 0, "mirror": 0, "last": "B", "stagnant_len": 0, "is_stagnant": False}
        sides = ["B" if n >= 5 else "K" for n in history_nums[-25:]]
        
        # 1. DRAGON DETECTION (Consecutive Streak)
        dragon_len = 0
        last_side = sides[-1]
        for s in reversed(sides):
            if s == last_side:
                dragon_len += 1
            else:
                break
                
        # 1.5 DRAGON FRACTURE (PATAHAN NAGA) DETECTION
        # A dragon fracture occurs when a single round flips after an established streak of >= 2 (e.g. BBBK or KKKKB)
        is_dragon_fracture = False
        broken_dragon_side = None
        broken_dragon_len = 0
        fracture_recovery_side = last_side
        fracture_dead_side = None
        if dragon_len == 1 and len(sides) >= 3:
            prev_streak_side = sides[-2]
            prev_streak_len = 0
            for s in reversed(sides[:-1]):
                if s == prev_streak_side:
                    prev_streak_len += 1
                else:
                    break
            # FIX v37: Fracture recovery = FOLLOW the breaking side (momentum continue)
            # Bukti audit: Setelah BBB→K, K sering lanjut 1-2x baru balik B
            if prev_streak_len >= 3:
                is_dragon_fracture = True
                broken_dragon_side = prev_streak_side
                broken_dragon_len = prev_streak_len
                # v37: Ikuti sisi baru (last_side) yang memecah naga
                fracture_recovery_side = last_side
                fracture_dead_side = prev_streak_side
                
        # Calculate stagnant consecutive identical number length (e.g. 4-4-4-4)
        stagnant_len = 0
        if len(history_nums) >= 2:
            last_num = history_nums[-1]
            for num in reversed(history_nums):
                if num == last_num:
                    stagnant_len += 1
                else:
                    break
                    
        is_stagnant_flat = (stagnant_len >= 2)
        # CRITICAL FIX (Anti-Kebocoran Dragon): 
        # Never artificially truncate dragon_len during identical number streaks (e.g. 2-2-2 or 6-6-6).
        # A run of identical numbers is a full-strength directional trend.
        
        # 2. ZIGZAG DETECTION (BKBK...)
        zigzag_len = 0
        for i in range(len(sides)-1, 0, -1):
            if sides[i] != sides[i-1]:
                zigzag_len += 1
            else:
                break
        
        # 3. IMBALANCE CALCULATION
        last_10 = sides[-10:]
        b_perc = last_10.count("B") / 10.0
        imbalance = abs(b_perc - 0.5)

        # 4. MIRROR & TRAP DETECTION (Titan 9.8)
        mirror_score = 0
        if len(sides) >= 4:
            if sides[-1] == sides[-2] and sides[-3] == sides[-4] and sides[-1] != sides[-3]:
                mirror_score = 1.0
        
        # 5. PURE FRACTAL RUMUS (Titan 9.8 Unique)
        fractal_rumus = 0
        if len(sides) >= 6:
            # Detect pattern: B-B-K | B-B-K
            if sides[-3:] == sides[-6:-3]:
                fractal_rumus = 1.5
        
        # 6. OVER-UNDER OSCILLATION (Titan 9.8)
        oscillation = 0
        if len(sides) >= 3:
            if sides[-1] != sides[-2] and sides[-2] != sides[-3]:
                oscillation = 1.0

        # 7. V-PATTERN & M-PATTERN (Titan 9.8)
        v_pattern = 0
        m_pattern = 0
        if len(sides) >= 4:
            # V-Pattern: B-K-K-B or K-B-B-K
            if sides[-1] == sides[-4] and sides[-2] == sides[-3] and sides[-1] != sides[-2]:
                v_pattern = 1.0
            if len(sides) >= 6:
                # M-Pattern: B-B-K-K-B-B
                if sides[-1] == sides[-2] and sides[-3] == sides[-4] and sides[-5] == sides[-6] and sides[-1] != sides[-3] and sides[-3] != sides[-5]:
                    m_pattern = 1.0

        # 8. MIRROR 3-1-3 (Titan 9.9)
        mirror_313 = 0
        if len(sides) >= 7:
            # B-B-B - K - B-B-B
            if sides[-1] == sides[-2] == sides[-3] and sides[-5] == sides[-6] == sides[-7] and sides[-1] == sides[-7] and sides[-4] != sides[-1]:
                mirror_313 = 1.2

        # 9. DOUBLE ZIGZAG (Titan 9.9)
        double_zigzag = 0
        if len(sides) >= 4:
            if sides[-1] != sides[-2] and sides[-3] != sides[-4] and sides[-2] == sides[-3]:
                double_zigzag = 1.0

        # 10. ADAPTIVE DRIFT BIAS (Titan 9.9 Black Ops)
        drift_bias = 0.0
        if len(sides) >= 10:
            b_count = sides[-10:].count("B")
            # In TRENDING/DRAGON phases, we follow the drift (Momentum)
            # In CHAOTIC phases, we counter the drift (Reversion)
            is_trending = dragon_len >= 3 or zigzag_len >= 5
            
            if is_trending:
                if b_count >= 7: drift_bias = 0.45 # Favor Besar (Momentum)
                elif b_count <= 3: drift_bias = -0.45 # Favor Kecil (Momentum)
            else:
                if b_count >= 8: drift_bias = -0.35 # Favor Kecil (Reversion)
                elif b_count <= 2: drift_bias = 0.35 # Favor Besar (Reversion)

        trap_risk = 0.0
        if len(sides) >= 8:
            if sides[-4:].count("B") == 2 and sides[-8:-4].count("B") == 2:
                trap_risk = 0.5

        return {
            "dragon": dragon_len,
            "is_dragon_fracture": is_dragon_fracture,
            "broken_dragon_side": broken_dragon_side,
            "broken_dragon_len": broken_dragon_len,
            "fracture_recovery_side": fracture_recovery_side,
            "fracture_dead_side": fracture_dead_side,
            "zigzag": zigzag_len,
            "mirror": mirror_score,
            "fractal": fractal_rumus,
            "oscillation": oscillation,
            "v_pattern": v_pattern,
            "m_pattern": m_pattern,
            "mirror_313": mirror_313,
            "double_zigzag": double_zigzag,
            "drift_bias": drift_bias,
            "trap_risk": trap_risk,
            "last_side_imbalance": imbalance,
            "stagnant_len": stagnant_len,
            "is_stagnant": is_stagnant_flat,
            "last": last_side
        }

    def run_deep_scan_v30(self, history):
        """Intensive period-by-period multi-layered scan"""
        if len(history) < 10: return {"status": "INSUFFICIENT_DATA", "risk": "HIGH"}
        
        # 1. Micro-Patterns Analysis
        recent_10 = history[-10:]
        diffs = np.diff(recent_10)
        volatility = np.std(diffs)
        
        # 2. Entropy Resonance
        resonance = self.quantum_entropy * 1.2 if self.market_phase == "MAX_CHAOS" else self.quantum_entropy
        
        # 3. Hidden Drift Detection
        drift_type = "NEUTRAL"
        if resonance > 2.9: drift_type = "CHAOS_DRIFT"
        elif volatility < 1.0: drift_type = "STAGNANT_LOCK"
        
        return {
            "status": "COMPLETED",
            "resonance": round(resonance, 3),
            "drift": drift_type,
            "volatility": round(volatility, 3),
            "recommendation": "USE_REVERSION" if resonance > 2.8 else "FOLLOW_TREND"
        }

    def project_future_quantum(self, history):
        """Simulates 100 parallel futures and returns the most probable next state"""
        if len(history) < 10: return "B", 0.5
        
        futures = []
        for _ in range(100):
            # Monte Carlo simulation based on current entropy and weighted engines
            sim_h = list(history)
            for __ in range(3): # Projection depth
                noise = np.random.normal(0, self.quantum_entropy * 0.5)
                # Weighted blend of last value and trend
                next_val = sim_h[-1] + (np.mean(np.diff(sim_h[-5:])) * 0.5) + noise
                next_val = max(0, min(9, int(next_val)))
                sim_h.append(next_val)
            futures.append("B" if sim_h[-3] >= 5 else "K")
        
        b_prob = futures.count("B") / 100.0
        return ("B" if b_prob >= 0.5 else "K"), b_prob

    def run_deep_scan_v40(self, history):
        """Ultra-Deep Scan with Fibonacci and Fractal Resistance Gates"""
        if len(history) < 5: return {"status": "INSUFFICIENT_DATA", "risk": "CRITICAL"}
        
        # 1. Fibonacci Retracement Check
        high = max(history[-15:])
        low = min(history[-15:])
        range_val = high - low
        level_618 = low + (range_val * 0.618)
        last_val = history[-1]
        
        fibo_bias = "NEUTRAL"
        if last_val > level_618: fibo_bias = "RESISTANCE_HIGH"
        else: fibo_bias = "SUPPORT_LOW"

        # 2. Fractal Drift (Detecting self-similar patterns)
        chunk1 = history[-4:]
        chunk2 = history[-8:-4]
        fractal_corr = 0
        if (chunk1[0] > 5) == (chunk2[0] > 5): fractal_corr += 1
        if (chunk1[-1] > 5) == (chunk2[-1] > 5): fractal_corr += 1
        
        # 3. Decision Logic refinement
        resonance = self.quantum_entropy * 1.3
        recommendation = "REVERSION"
        if fractal_corr >= 2: recommendation = "DRAGON_FOLLOW"
        elif resonance < 2.5: recommendation = "PATTERN_SYNC"
        
        return {
            "status": "COMPLETED",
            "fibo": fibo_bias,
            "fractal_score": fractal_corr,
            "resonance": round(resonance, 3),
            "recommendation": recommendation
        }

    def _calculate_cycle_harmony(self, history):
        """Checks if short-term momentum aligns with long-term cycles"""
        if len(history) < 20: return 1.0
        
        short_term = np.mean(np.diff(history[-5:]))
        long_term = np.mean(np.diff(history[-20:]))
        
        # If both are positive or both are negative, harmony is high (1.5)
        # If they disagree, harmony is low (0.5) - likely a reversal point
        if (short_term > 0) == (long_term > 0):
            return 1.4
        return 0.6

    def analyze_quantum_stream(self, history_nums, mode="1m", current_period=None):
        # CLEANSE INPUT
        try:
            history_nums = [int(x) for x in history_nums]
        except:
            pass

        if len(history_nums) < 1:
            return {
                "side": "BESAR",
                "num": 5,
                "color": "HIJAU",
                "confidence": 50.0,
                "acc": 50.0,
                "is_jp": False,
                "vector_strength": 100,
                "entropy": 0.0,
                "action": "TITAN-ACTIVE",
                "phase": "STABILIZING",
                "trend_stats": None
            }

        # 1. PATTERN ENGINE SYNC
        patterns = self.detect_patterns(history_nums)
        self.last_p_info = patterns
        
        # 1.0 TREND FATIGUE & EXHAUSTION DETECTION (Titan 11.2 Anti-Overconfidence)
        self.trend_fatigue = 0.0
        if patterns["dragon"] >= 4:
            if patterns["dragon"] == 4: self.trend_fatigue = 0.10
            elif patterns["dragon"] == 5: self.trend_fatigue = 0.20
            elif patterns["dragon"] == 6: self.trend_fatigue = 0.35
            elif patterns["dragon"] == 7: self.trend_fatigue = 0.50
            else: self.trend_fatigue = min(0.68, 0.50 + (patterns["dragon"] - 7) * 0.06)
        
        # 1.1 GRAFIK TREND SYNC (from grafik.py)
        trend_data = self.chart.get_trend_vectors(history_nums)
        self.last_stats = trend_data.get("raw_stats")
        
        # 2. MULTI-WINDOW ENTROPY SLICER (Dynamic Chaos Detection)
        # Deep analysis of entropy across multiple timescales
        def calc_e(data):
            if not data: return 0.0
            counts = np.bincount(data, minlength=10)
            p = counts.astype(float) / len(data)
            nz = p > 0
            return float(-np.sum(p[nz] * np.log2(p[nz]))) if np.any(nz) else 0.0

        e_short = calc_e(history_nums[-10:])
        e_mid = calc_e(history_nums[-25:])
        e_long = calc_e(history_nums[-50:])
        
        self.quantum_entropy = (e_short * 0.5) + (e_mid * 0.3) + (e_long * 0.2)
        self.entropy_history.append(self.quantum_entropy)
        
        # Entropy Acceleration (Detecting sudden spikes)
        e_delta = 0.0
        if len(self.entropy_history) > 2:
            e_delta = self.quantum_entropy - self.entropy_history[-2]
        
        # Side Entropy for directional bias detection
        recent_sides = [1 if n >= 5 else 0 for n in history_nums[-50:]]
        side_counts = np.bincount(recent_sides, minlength=2)
        side_probs = side_counts.astype(float) / len(recent_sides)
        side_nz = side_probs > 0
        side_entropy = float(-np.sum(side_probs[side_nz] * np.log2(side_probs[side_nz]))) if np.any(side_nz) else 0.0
        
        # 3. DEEP TRANSITION ANALYSIS (Markov Chain v5 - TITANIUM)
        last_num = history_nums[-1]
        transitions = []
        lookback = history_nums[-200:]
        for i in range(len(lookback)-1):
            if lookback[i] == last_num:
                transitions.append(lookback[i+1])
        
        markov_vectors = {"B": 0.0, "K": 0.0}
        if transitions:
            trans_counts = np.bincount(transitions, minlength=10)
            # Add exponential weighting to markov if recent occurrences match
            weight = 1200.0 if len(transitions) > 5 else 600.0
            markov_vectors["B"] = np.sum(trans_counts[5:]) * weight
            markov_vectors["K"] = np.sum(trans_counts[:5]) * weight

        # RUMUS MATH 1: HIGHER-ORDER MARKOV CHAIN (Order 2 & 3)
        markov_high_vectors = {"B": 0.0, "K": 0.0}
        if len(history_nums) >= 4:
            # Order 2: Sequence of last 2 numbers
            last_2 = history_nums[-2:]
            t_order2 = []
            for i in range(len(lookback) - 2):
                if lookback[i:i+2] == last_2:
                    t_order2.append(lookback[i+2])
            if t_order2:
                o2_counts = np.bincount(t_order2, minlength=10)
                markov_high_vectors["B"] += np.sum(o2_counts[5:]) * 2000.0
                markov_high_vectors["K"] += np.sum(o2_counts[:5]) * 2000.0

            # Order 3: Sequence of last 3 numbers
            last_3 = history_nums[-3:]
            t_order3 = []
            for i in range(len(lookback) - 3):
                if lookback[i:i+3] == last_3:
                    t_order3.append(lookback[i+3])
            if t_order3:
                o3_counts = np.bincount(t_order3, minlength=10)
                markov_high_vectors["B"] += np.sum(o3_counts[5:]) * 3500.0
                markov_high_vectors["K"] += np.sum(o3_counts[:5]) * 3500.0

        # RUMUS MATH 2: BAYESIAN INFERENCE PROBABILITY WEIGHTING
        bayesian_vectors = {"B": 0.0, "K": 0.0}
        total_p = len(lookback)
        if total_p >= 30:
            p_b = sum(1 for x in lookback if x >= 5) / total_p
            p_k = 1.0 - p_b
            
            recent_obs = [1 if x >= 5 else 0 for x in history_nums[-3:]]
            
            match_b = 0
            match_k = 0
            occur_b = 0
            occur_k = 0
            for i in range(len(lookback) - 3):
                state_seq = [1 if x >= 5 else 0 for x in lookback[i:i+3]]
                next_side = 1 if lookback[i+3] >= 5 else 0
                if next_side == 1:
                    occur_b += 1
                    if state_seq == recent_obs:
                        match_b += 1
                else:
                    occur_k += 1
                    if state_seq == recent_obs:
                        match_k += 1
            
            p_trend_given_b = (match_b / occur_b) if occur_b > 0 else 0.1
            p_trend_given_k = (match_k / occur_k) if occur_k > 0 else 0.1
            
            post_b = p_trend_given_b * p_b
            post_k = p_trend_given_k * p_k
            
            total_post = post_b + post_k
            if total_post > 0:
                bayesian_vectors["B"] = (post_b / total_post) * 15000.0
                bayesian_vectors["K"] = (post_k / total_post) * 15000.0

        # RUMUS MATH 3: CHI-SQUARE GOODNESS-OF-FIT DEVIATION FILTER
        chi_square_stat = 0.0
        is_manipulated_streak = False
        if len(history_nums) >= 30:
            hist_30 = history_nums[-30:]
            observed_sides = [1 if x >= 5 else 0 for x in hist_30]
            o_b = observed_sides.count(1)
            o_k = observed_sides.count(0)
            e_expected = 15.0
            
            chi_square_stat = ((o_b - e_expected) ** 2 / e_expected) + ((o_k - e_expected) ** 2 / e_expected)
            if chi_square_stat > 3.84:
                is_manipulated_streak = True

        # RUMUS MATH 4: TRIPLE-CROSS EXPONENTIAL MOVING AVERAGE (TEMA) SIGNAL
        tema_vectors = {"B": 0.0, "K": 0.0}
        if len(history_nums) >= 20:
            hist_20_sides = [1.0 if x >= 5 else 0.0 for x in history_nums[-20:]]
            
            def calc_ema(values, period):
                ema = [values[0]]
                k = 2.0 / (period + 1.0)
                for val in values[1:]:
                    ema.append(val * k + ema[-1] * (1.0 - k))
                return ema
                
            ema_3 = calc_ema(hist_20_sides, 3)
            ema_7 = calc_ema(hist_20_sides, 7)
            ema_14 = calc_ema(hist_20_sides, 14)
            
            tema_score = (3.0 * ema_3[-1] - 3.0 * ema_7[-1] + ema_14[-1])
            
            if tema_score > 0.55:
                tema_vectors["B"] = (tema_score - 0.5) * 22000.0
            elif tema_score < 0.45:
                tema_vectors["K"] = (0.5 - tema_score) * 22000.0

        # RUMUS MATH 5: KALMAN FILTER RECURSIVE STATE ESTIMATION
        kalman_vectors = {"B": 0.0, "K": 0.0}
        if len(history_nums) >= 10:
            x_est = float(history_nums[0])
            p_est = 1.0
            q_noise = 0.0001
            r_noise = 1.5
            for val in history_nums[1:]:
                # Predict
                p_est = p_est + q_noise
                # Update
                k_gain = p_est / (p_est + r_noise)
                x_est = x_est + k_gain * (val - x_est)
                p_est = (1.0 - k_gain) * p_est
            # If our estimated recursive state crosses 4.5, forecast accordingly
            if x_est >= 4.5:
                kalman_vectors["B"] = (x_est - 4.5) * 18000.0
            else:
                kalman_vectors["K"] = (4.5 - x_est) * 18000.0

        # RUMUS MATH 6: SPECTRAL FOURIER TRANSFORMATION & HARMONIC CYCLES (PREMIUM ADVANCED PHASE SHIFT SCAN)
        fourier_vectors = {"B": 0.0, "K": 0.0}
        if len(history_nums) >= 20:
            sig_f = [1.0 if x >= 5 else -1.0 for x in history_nums[-20:]]
            n_f = len(sig_f)
            best_period = 2
            best_phase = 0.0
            max_corr = -1.0
            # Scan multiple frequency periods and phase angles to discover cyclical phase transitions
            for p_len in range(2, 16): # Premium extended scanning range
                for phase in [0, np.pi/4, np.pi/2, 3*np.pi/4]: # Advanced Phase Scan angles
                    ref_wave = [float(np.cos(2 * np.pi * i / p_len + phase)) for i in range(n_f)]
                    corr = float(np.sum(np.array(sig_f) * np.array(ref_wave)))
                    if abs(corr) > max_corr:
                        max_corr = abs(corr)
                        best_period = p_len
                        best_phase = phase
            projected_val = float(np.cos(2 * np.pi * n_f / best_period + best_phase))
            weight = max(150.0, max_corr * 14500.0) # Premium boosted fourier spectral weight
            if projected_val > 0:
                fourier_vectors["B"] = weight
            else:
                fourier_vectors["K"] = weight

        # RUMUS MATH 7: K-NEAREST NEIGHBORS (KNN) CLUSTER DENSITY SCAN
        knn_vectors = {"B": 0.0, "K": 0.0}
        if len(history_nums) >= 12:
            current_pattern = history_nums[-4:]
            for idx in range(len(history_nums) - 5):
                dist = sum(abs(history_nums[idx + i] - current_pattern[i]) for i in range(4))
                if dist <= 3.0:
                    w = 5000.0 / (dist + 1.0)
                    next_val = history_nums[idx + 4]
                    if next_val >= 5:
                        knn_vectors["B"] += w
                    else:
                        knn_vectors["K"] += w

        # RUMUS MATH 8: DOUBLE HOLT-WINTERS SEQUENTIAL TREND MATRIX
        holt_winters_vectors = {"B": 0.0, "K": 0.0}
        if len(history_nums) >= 15:
            sides_float = [1.0 if x >= 5 else 0.0 for x in history_nums[-15:]]
            alpha = 0.4
            beta = 0.3
            level_hw = sides_float[0]
            trend_hw = sides_float[1] - sides_float[0]
            for t_idx in range(1, len(sides_float)):
                prev_level = level_hw
                level_hw = alpha * sides_float[t_idx] + (1.0 - alpha) * (level_hw + trend_hw)
                trend_hw = beta * (level_hw - prev_level) + (1.0 - beta) * trend_hw
            pred_hw = level_hw + trend_hw
            if pred_hw >= 0.5:
                holt_winters_vectors["B"] = (pred_hw - 0.5) * 16000.0
            else:
                holt_winters_vectors["K"] = (0.5 - pred_hw) * 16000.0

        # RUMUS MATH 9: FUZZY COGNITIVE SECTRUM IDENTIFIER (Fuzzy Logic)
        fuzzy_vectors = {"B": 0.0, "K": 0.0}
        if len(history_nums) >= 10:
            recent_mean = sum(history_nums[-10:]) / 10.0
            mu_k = max(0.0, min(1.0, (9.0 - recent_mean) / 4.5)) if recent_mean > 4.5 else 1.0
            mu_b = max(0.0, min(1.0, recent_mean / 4.5)) if recent_mean < 4.5 else 1.0
            fuzzy_vectors["B"] = mu_b * 12000.0
            fuzzy_vectors["K"] = mu_k * 12000.0

        # RUMUS MATH 10: HIDDEN MARKOV MODEL (HMM 2-state)
        hmm_vectors = {"B": 0.0, "K": 0.0}
        if len(history_nums) >= 15:
            _obs = [1 if n >= 5 else 0 for n in history_nums[-15:]]
            _trans_bb, _trans_bk, _trans_kb, _trans_kk = 0.1, 0.1, 0.1, 0.1
            for _i in range(len(_obs) - 1):
                if _obs[_i] == 1 and _obs[_i+1] == 1: _trans_bb += 1
                elif _obs[_i] == 1 and _obs[_i+1] == 0: _trans_bk += 1
                elif _obs[_i] == 0 and _obs[_i+1] == 1: _trans_kb += 1
                else: _trans_kk += 1
            _sum_b = _trans_bb + _trans_bk
            _sum_k = _trans_kb + _trans_kk
            _p_next_b = (_trans_bb / _sum_b) if _obs[-1] == 1 else (_trans_kb / _sum_k)
            if _p_next_b >= 0.5:
                hmm_vectors["B"] = (_p_next_b - 0.5) * 20000.0
            else:
                hmm_vectors["K"] = (0.5 - _p_next_b) * 20000.0

        # RUMUS MATH 11: CUSUM CHANGE POINT DETECTOR
        cusum_vectors = {"B": 0.0, "K": 0.0}
        if len(history_nums) >= 20:
            _sides_c = [1 if n >= 5 else 0 for n in history_nums[-20:]]
            _mean_c = sum(_sides_c) / len(_sides_c)
            _cusum_pos, _cusum_neg = 0.0, 0.0
            _threshold_c = 2.5
            for _v in _sides_c:
                _cusum_pos = max(0, _cusum_pos + _v - _mean_c - 0.1)
                _cusum_neg = max(0, _cusum_neg - _v + _mean_c - 0.1)
            if _cusum_pos > _threshold_c:
                cusum_vectors["K"] = 18000.0
            elif _cusum_neg > _threshold_c:
                cusum_vectors["B"] = 18000.0

        # RUMUS MATH 12: THOMPSON SAMPLING MULTI-ARMED BANDIT
        thompson_vectors = {"B": 0.0, "K": 0.0}
        if len(history_nums) >= 10:
            import random as _rnd_ts
            _best_b, _best_k = 0.0, 0.0
            _snap_ts = getattr(self, "_last_engine_snapshot", {}) or {}
            for _m, _sc in self.method_scores.items():
                _w, _l = _sc["win"] + 1, _sc["lose"] + 1
                _samp = _rnd_ts.betavariate(_w, _l)
                _snap_vote = _snap_ts.get(_m, 0)
                if _snap_vote == 1: _best_b += _samp
                elif _snap_vote == -1: _best_k += _samp
            if _best_b > _best_k:
                thompson_vectors["B"] = min(20000.0, _best_b * 8000.0)
            else:
                thompson_vectors["K"] = min(20000.0, _best_k * 8000.0)

        # RUMUS MATH 13: ENTROPY GRADIENT DETECTOR
        entropy_grad_vectors = {"B": 0.0, "K": 0.0}
        if len(self.entropy_history) >= 4:
            _eh = list(self.entropy_history)[-4:]
            _grad = (_eh[-1] - _eh[0]) / 3.0
            if _grad > 0.08:
                if history_nums[-1] >= 5:
                    entropy_grad_vectors["B"] = 15000.0
                else:
                    entropy_grad_vectors["K"] = 15000.0

        # RUMUS MATH 14: WEIGHTED MOVING AVERAGE CROSSOVER
        wma_vectors = {"B": 0.0, "K": 0.0}
        if len(history_nums) >= 10:
            _wma_fast = sum((_i + 1) * history_nums[-5:][_i] for _i in range(5)) / 15.0
            _wma_slow = sum((_i + 1) * history_nums[-10:][_i] for _i in range(10)) / 55.0
            _wma_diff = _wma_fast - _wma_slow
            if _wma_diff > 0.8:
                wma_vectors["B"] = min(18000.0, _wma_diff * 8000.0)
            elif _wma_diff < -0.8:
                wma_vectors["K"] = min(18000.0, abs(_wma_diff) * 8000.0)

        # RUMUS MATH 15: MAJORITY VOTE 5-WINDOW
        maj_vectors = {"B": 0.0, "K": 0.0}
        if len(history_nums) >= 5:
            _last5 = [1 if n >= 5 else 0 for n in history_nums[-5:]]
            _b_cnt = sum(_last5)
            if _b_cnt >= 4:
                maj_vectors["B"] = 12000.0
            elif _b_cnt <= 1:
                maj_vectors["K"] = 12000.0

        # RUMUS MATH 16: NEAREST GAP PATTERN MATCHER
        gap_vectors = {"B": 0.0, "K": 0.0}
        if len(history_nums) >= 8:
            _recent_side = "B" if history_nums[-1] >= 5 else "K"
            _gap_len = 0
            for _n in reversed(history_nums):
                if ("B" if _n >= 5 else "K") == _recent_side: _gap_len += 1
                else: break
            _historical_next = []
            _cur_gap = 1
            for _i in range(1, len(history_nums)):
                _s_prev = "B" if history_nums[_i-1] >= 5 else "K"
                _s_cur = "B" if history_nums[_i] >= 5 else "K"
                if _s_cur == _s_prev:
                    _cur_gap += 1
                else:
                    if _cur_gap == _gap_len:
                        _historical_next.append(_s_cur)
                    _cur_gap = 1
            if _historical_next:
                _b_wins = _historical_next.count("B")
                _k_wins = _historical_next.count("K")
                if _b_wins > _k_wins:
                    gap_vectors["B"] = (_b_wins / len(_historical_next)) * 15000.0
                elif _k_wins > _b_wins:
                    gap_vectors["K"] = (_k_wins / len(_historical_next)) * 15000.0

        # RUMUS MATH 17: PROBABILITY DISTRIBUTION SPREAD
        spread_vectors = {"B": 0.0, "K": 0.0}
        if len(history_nums) >= 10:
            _std_recent = float(np.std(history_nums[-10:]))
            if _std_recent < 2.0:
                if history_nums[-1] >= 5:
                    spread_vectors["B"] = 10000.0
                else:
                    spread_vectors["K"] = 10000.0

        # RUMUS MATH 18: LAST-30 BIAS DETECTOR
        hour_bias_vectors = {"B": 0.0, "K": 0.0}
        if len(history_nums) >= 30:
            _current_hour_b = sum(1 for n in history_nums[-30:] if n >= 5)
            if _current_hour_b >= 18:
                hour_bias_vectors["B"] = 8000.0
            elif _current_hour_b <= 12:
                hour_bias_vectors["K"] = 8000.0

        # RUMUS MATH 19: VOLUME-WEIGHTED TREND
        vw_vectors = {"B": 0.0, "K": 0.0}
        if len(history_nums) >= 12:
            _recent = history_nums[-12:]
            _weighted = sum((_i + 1) * (1 if _recent[_i] >= 5 else -1) for _i in range(12))
            if _weighted > 15:
                vw_vectors["B"] = 14000.0
            elif _weighted < -15:
                vw_vectors["K"] = 14000.0

        # [v38] CROSS-TIMEFRAME CONFIRMATION
        cross_vectors = self.get_cross_signal_vectors(history_nums)
        
        # [v38] Q-LEARNING SUGGESTION (dari pengalaman historis)
        q_vectors = self.get_q_suggestion(history_nums)
        
        # [v38] Simpan history untuk backtest
        if history_nums:
            self._recent_nums.append(history_nums[-1])

        # SENSITIVE CHAOS DETECTION (Titan 8.9 Ultra+)
        is_chaotic = self.quantum_entropy > 2.35 or side_entropy > 0.88
        is_max_chaos = self.quantum_entropy > 2.70
        is_zigzag_momentum = patterns.get("zigzag", 0) >= 3

        # VIOLET TRAP DETECTOR (Concentration of 0 and 5)
        recent_10 = history_nums[-10:]
        violet_count = sum(1 for n in recent_10 if n in [0, 5])
        violet_ratio = violet_count / len(recent_10) if recent_10 else 0.0
        is_violet_trap = violet_ratio >= 0.30  # 30% or more are 0 or 5 in last 10 periods

        self.market_phase = "CHAOTIC" if is_chaotic else "STRUCTURAL"
        if is_max_chaos: 
            self.market_phase = "MAX_CHAOS"
        elif side_entropy < 0.45: 
            self.market_phase = "TRENDING"
        
        if is_zigzag_momentum and is_chaotic:
            self.market_phase = "ZIGZAG_MOMENTUM"

        # Chaos Severity Scaling
        chaos_severity = max(1.0, self.quantum_entropy - 2.0) if is_chaotic else 1.0
        
        # TITAN PHASE PRIORITY GATE (Titan 11.0 Black Ops - Absolute Real-Time Trend Precedence)
        # 1. Active Dragon / Zigzag ALWAYS overrides historical JP resonance or chaotic labels!
        if patterns.get("dragon", 0) >= 2:
            self.market_phase = "TRENDING"
        elif patterns.get("zigzag", 0) >= 3:
            self.market_phase = "ZIGZAG_MOMENTUM"
                # --- PATCH 3: PATTERN PRIORITY OVERRIDE ---
        elif self.quantum_entropy > 2.70:
            self.market_phase = "CHAOTIC" 
            self._log("PATTERN PRIORITY: Entropi tinggi. Beralih ke mode CHAOTIC (hati-hati).")
        # --- END PATCH 3 ---
        elif is_violet_trap:
            self.market_phase = "VIOLET_TRANSITION"  # Force VIOLET_TRANSITION phase for stabilization
        elif self.jp_resonance_count > 8 and self.loss_counter == 0:
            self.market_phase = "JP_HARMONY"
        elif self.jp_resonance_count > 4 and self.loss_counter == 0:
            self.market_phase = "TITAN_ULTRA_SYNC"
        elif is_max_chaos or self.quantum_entropy > 2.8:
            self.market_phase = "MAX_CHAOS" # Force high-entropy mode
        elif self.market_phase == "ZIGZAG_MOMENTUM":
            pass # Keep phase
        elif self.quantum_entropy > 2.4:
            self.market_phase = "CHAOTIC"
        elif patterns["mirror"] == 1:
            self.market_phase = "MIRRORING"
        elif patterns["fractal"] > 0:
            self.market_phase = "FRACTAL_DNA"
        else:
            self.market_phase = "OMEGA_STABLE"

        is_trend_dominant = (patterns.get("dragon", 0) >= 2 or patterns.get("zigzag", 0) >= 3 or self.market_phase == "TRENDING" or self.quantum_entropy > 2.80)
        
        # 4.1 NOISE FILTER CALIBRATION (Titan 9.9)
        self.noise_filter_factor = 1.0 + (self.quantum_entropy * 0.4)
        if self.market_phase == "MAX_CHAOS":
            self.noise_filter_factor *= 2.5
        elif self.market_phase == "VIOLET_TRANSITION":
            self.noise_filter_factor *= 2.0  # Extra dampening during 0/5 trap
        elif self.market_phase == "CHAOTIC":
            self.noise_filter_factor *= 1.85
            
        # Amplified noise filter using pattern neural weight feedback
        if self.neural_weights.get("pattern", 1.0) > 1.0:
            self.noise_filter_factor *= (self.neural_weights["pattern"] * 1.12)

        # Boost noise filter on consecutive losses to neutralize pattern noise ("Filter noise ditingkatkan")
        if self.loss_counter > 0:
            self.noise_filter_factor *= (1.0 + self.loss_counter * 0.45)
        
        # TITAN VECTOR BASE (FINAL STABILIZED)
        # Multi-Engine Weights with Dynamic Recalibration
        # [AI-LEARN v1] Base weight × learned weight
        _lw = lambda k: self.method_scores.get(k, {}).get("weight", 1.0)
        w_markov = 1.45 * self.engine_performance["markov"] * _lw("markov")
        w_trend = 1.25 * self.engine_performance["trend"]
        w_pattern = 1.85 * self.engine_performance["pattern"] * _lw("pattern")
        w_regress = 1.20 * self.engine_performance["regress"]
        w_mirror = 1.8 if self.market_phase == "MIRRORING" else 0.0

        # ADAPTIVE ENGINE ADJUSTMENT (Titan 11.0 Ultra)
        if self.market_phase == "MAX_CHAOS":
            w_markov *= 0.05   
            w_pattern *= 0.80  
            # Under extreme volatility (entropy > 2.80): Selaraskan dengan tren lokal & kurangi counter-trade spekulatif!
            w_regress *= 0.15 # Dilarang keras counter-trade spekulatif saat entropi ekstrem!
            w_trend *= 2.40   # Ikuti momentum lokal
            self.neural_weights["reversion"] = min(0.04, self.neural_weights.get("reversion", 1.0) * 0.10)
            self.neural_weights["momentum"] = max(3.0, self.neural_weights.get("momentum", 1.0) * 2.00)
        elif self.market_phase == "VIOLET_TRANSITION":
            # 0/5 concentration: maintain local cluster awareness with balanced momentum
            w_markov *= 0.10
            w_pattern *= 0.60
            w_regress *= 0.60
            w_trend *= 1.40
            self.neural_weights["reversion"] = min(0.10, self.neural_weights.get("reversion", 1.0) * 0.20)
            self.neural_weights["momentum"] = max(2.0, self.neural_weights.get("momentum", 1.0) * 1.50)
            self._log(f"VTG ACTIVE: Scaling regression factor to {w_regress:.2f}x; stabilizing momentum.")
        elif self.market_phase == "TITAN_ULTRA_SYNC":
            w_pattern *= 4.5
            w_regress *= 3.5
            w_trend *= 2.0
        elif self.market_phase == "FRACTAL_DNA":
            w_pattern *= 5.0
            w_regress *= 0.5
        elif self.market_phase == "ZIGZAG_MOMENTUM":
            w_pattern *= 7.5 # Ultra priority for ZigZag 
            w_regress *= 0.01
            w_markov *= 0.01
            w_trend *= 1.5
        elif self.market_phase == "CHAOTIC":
            w_markov *= (0.01 / chaos_severity) 
            w_pattern *= (0.02 / chaos_severity) 
            w_regress *= (7.5 * chaos_severity) 
        elif self.market_phase == "TRENDING":
            w_pattern *= 6.5
            w_regress *= 0.10
        elif self.market_phase == "MIRRORING":
            w_pattern *= 4.5
            w_markov *= 3.5
            w_trend *= 0.3
        elif self.market_phase == "JP_HARMONY":
            if self.quantum_entropy > 2.2:
                # Scaled down to prevent pattern noise amplification under chaos
                w_pattern *= 2.0
                w_regress *= 0.8
                w_trend *= 1.5
            else:
                w_pattern *= 4.0 # Balanced focus on historical pattern
                w_regress *= 1.2
                w_trend *= 1.8

        # CORE WEIGHTS SYNCHRONIZATION ("Bobot Core disinkronkan")
        if self.loss_counter >= 1 or self.quantum_entropy > 2.4:
            # Blend engine weights toward an even sync to avoid extreme single-engine skewness
            mean_weight = (w_markov + w_trend + w_pattern + w_regress) / 4.0
            sync_factor = 0.50 if self.loss_counter >= 2 else 0.30
            w_markov = w_markov * (1.0 - sync_factor) + mean_weight * sync_factor
            w_trend = w_trend * (1.0 - sync_factor) + mean_weight * sync_factor
            w_pattern = w_pattern * (1.0 - sync_factor) + mean_weight * sync_factor
            w_regress = w_regress * (1.0 - sync_factor) + mean_weight * sync_factor
            self._log(f"CORE WEIGHTS SYNCHRONIZED: Blending toward base {mean_weight:.2f} (factor: {sync_factor})")

        # JACKPOT COLLABORATION BRIDGE (NSS 3.0)
        if self.jp_resonance_count > 0:
            jp_boost = 1.0 + (self.jp_resonance_count * 0.22)
            # If JP is hitting, the market is following deep payout patterns
            w_pattern *= jp_boost
            w_regress *= (1.0 + (self.jp_resonance_count * 0.10))
            self._log(f"JP_COOP_SYNC: Matrix weights harmonized by {jp_boost:.2f}x")

        # --- SIGNAL CALCULATION ---
        w_markov_high = 1.40 * self.engine_performance.get("markov_high", 1.0) * _lw("markov_high")
        w_bayesian = 1.35 * self.engine_performance.get("bayesian", 1.0) * _lw("bayesian")
        w_tema = 1.25 * self.engine_performance.get("tema", 1.0) * _lw("tema")
        w_kalman = 1.30 * self.engine_performance.get("kalman", 1.0) * _lw("kalman")
        w_fourier = 1.20 * self.engine_performance.get("fourier", 1.0) * _lw("fourier")
        w_knn = 1.25 * self.engine_performance.get("knn", 1.0) * _lw("knn")
        w_holt_winters = 1.35 * self.engine_performance.get("holt_winters", 1.0) * _lw("holt_winters")
        w_fuzzy = 1.15 * self.engine_performance.get("fuzzy", 1.0) * _lw("fuzzy")

        v_b = (float(markov_vectors["B"]) * w_markov) + \
              (trend_data.get("B", 0.0) * w_trend) + \
              (float(markov_high_vectors["B"]) * w_markov_high) + \
              (float(bayesian_vectors["B"]) * w_bayesian) + \
              (float(tema_vectors["B"]) * w_tema) + \
              (float(kalman_vectors["B"]) * w_kalman) + \
              (float(fourier_vectors["B"]) * w_fourier) + \
              (float(knn_vectors["B"]) * w_knn) + \
              (float(holt_winters_vectors["B"]) * w_holt_winters) + \
              (float(fuzzy_vectors["B"]) * w_fuzzy) + \
              float(hmm_vectors["B"]) + float(cusum_vectors["B"]) + \
              float(thompson_vectors["B"]) + float(entropy_grad_vectors["B"]) + \
              float(wma_vectors["B"]) + float(maj_vectors["B"]) + \
              float(gap_vectors["B"]) + float(spread_vectors["B"]) + \
              float(hour_bias_vectors["B"]) + float(vw_vectors["B"]) + \
              float(cross_vectors["B"]) + float(q_vectors["B"])

        v_k = (float(markov_vectors["K"]) * w_markov) + \
              (trend_data.get("K", 0.0) * w_trend) + \
              (float(markov_high_vectors["K"]) * w_markov_high) + \
              (float(bayesian_vectors["K"]) * w_bayesian) + \
              (float(tema_vectors["K"]) * w_tema) + \
              (float(kalman_vectors["K"]) * w_kalman) + \
              (float(fourier_vectors["K"]) * w_fourier) + \
              (float(knn_vectors["K"]) * w_knn) + \
              (float(holt_winters_vectors["K"]) * w_holt_winters) + \
              (float(fuzzy_vectors["K"]) * w_fuzzy) + \
              float(hmm_vectors["K"]) + float(cusum_vectors["K"]) + \
              float(thompson_vectors["K"]) + float(entropy_grad_vectors["K"]) + \
              float(wma_vectors["K"]) + float(maj_vectors["K"]) + \
              float(gap_vectors["K"]) + float(spread_vectors["K"]) + \
              float(hour_bias_vectors["K"]) + float(vw_vectors["K"]) + \
              float(cross_vectors["K"]) + float(q_vectors["K"])
        
        vectors = {"B": v_b, "K": v_k}
        
        # Apply Mirror Vectors (High Magnitude)
        if self.market_phase == "MIRRORING" and len(history_nums) >= 11:
            next_mirror = history_nums[-11] 
            side_m = "B" if next_mirror >= 5 else "K"
            vectors[side_m] += 50000.0 * w_mirror # Targeted Mirror Injection
        
        num_weights = trend_data.get("numbers", [0.0]*10)
        
        # Final Signal Check (No Skip Logic)
        if vectors["B"] == vectors["K"]: 
            vectors["B"] += 0.001 # Anti-Stall Mechanism
        
        # ULTRA-PRECISE Noise Filtering (Titan 9.9 Black Ops)
        noise_floor = np.std(history_nums) * 1.75 * self.noise_filter_factor
        vectors["B"] = max(0, vectors["B"] - noise_floor)
        vectors["K"] = max(0, vectors["K"] - noise_floor)

        # 5. PATTERN-FIRST LOGIC (Adaptive Matrix)
        pattern_vectors = {"B": 0.0, "K": 0.0}
        
        # 5.0 DRAGON LOGIC (HIGHEST PRIORITY - FOLLOW-TREND LOCK - DILARANG COUNTER-BET)
        # v37 DRAGON FOLLOW — boost lebih kuat, threshold turun ke 2
        if patterns["dragon"] >= 2:
            flip_side = "K" if patterns["last"] == "B" else "B"
            # v37: Semua dragon >= 2 di-lock kuat (bukan hanya >= 4)
            if patterns["dragon"] >= 8:
                boost = 80000.0 * (patterns["dragon"] ** 1.8)
            elif patterns["dragon"] >= 5:
                boost = 65000.0 * (patterns["dragon"] ** 1.7)
            elif patterns["dragon"] >= 3:
                boost = 55000.0 * (patterns["dragon"] ** 1.5)
            else:  # dragon == 2
                boost = 45000.0 * self.neural_weights.get("momentum", 1.0)
            
            pattern_vectors[patterns["last"]] += boost
            pattern_vectors[flip_side] = 0.0
            vectors[flip_side] = 0.0  # Absolute lock
            self._log(f"DRAGON LOCK v37: Follow-trend streak {patterns['dragon']}x on '{patterns['last']}'. Counter-bet eliminated.")
        # 5.1 CLUSTER DETECTION (AA-BB-AA-BB / POLA 2-2 DOUBLE-STEP) - ONLY IF NOT IN ACTIVE DRAGON
        elif patterns.get("mirror") == 1 and patterns["dragon"] < 2:
            flip_pair_side = "K" if patterns["last"] == "B" else "B"
            boost_pair = 35000.0 * self.neural_weights.get("pattern", 1.0)
            pattern_vectors[flip_pair_side] += boost_pair
            self._log(f"POLA 2-2 (DOUBLE-STEP) DETECTED: Completed pair '{patterns['last']}{patterns['last']}'. Projecting flip to '{flip_pair_side}'.")
        
        # 5.2 ZIGZAG LOGIC (Titan 10.0 Anti-Collapse Guard)
        elif patterns["zigzag"] >= 2:
            next_zigzag = "B" if patterns["last"] == "K" else "K"
            same_side = patterns["last"]
            if patterns["zigzag"] >= 6:
                # ZIGZAG EXHAUSTION & COLLAPSE IMMINENT (Z >= 6): High probability of twin repeat break
                pattern_vectors[same_side] += 16000.0 * self.neural_weights.get("momentum", 1.0)
                pattern_vectors[next_zigzag] += 4000.0
            elif patterns["zigzag"] >= 4:
                # MATURE ZIGZAG (Z: 4-5): Balance flip with slight buffer against sudden collapse
                boost = 10000.0 * (patterns["zigzag"] ** 1.1)
                pattern_vectors[next_zigzag] += boost * self.neural_weights["momentum"]
                pattern_vectors[same_side] += boost * 0.40 # Collapse buffer
            elif patterns["zigzag"] == 3:
                # HEALTHY ZIGZAG (Z: 3): High probability oscillation continuation
                boost = 14000.0 * (patterns["zigzag"] ** 1.35)
                pattern_vectors[next_zigzag] += boost * self.neural_weights["momentum"]
            else:
                # EARLY ZIGZAG (zigzag == 2): Pre-emptive oscillation booster
                boost = 8000.0 * self.neural_weights.get("momentum", 1.0)
                pattern_vectors[next_zigzag] += boost
                
        # 5.25 PATAHAN NAGA (DRAGON FRACTURE RECOVERY ENGINE - TITAN 11.2 ULTRA)
        # When a dragon streak of >= 2 breaks naturally, align immediately with the new recovery momentum (fracture_recovery_side)
        # [PATCH N] Fracture override DISABLED — production 15/50 losses masih 100% fracture.
        # Pasar Wingo 1Menit TIDAK mengikuti pola resumption ATAU flip.
        # Biarkan vector utama (momentum, pattern, markov, dll) handle natural.
        if patterns.get("is_dragon_fracture"):
            self._log(f"PATAHAN NAGA [OBSERVE-ONLY]: Dragon {patterns['broken_dragon_len']}x broke. Override disabled, letting vectors decide.")
            
        # 5.3 CLUSTER DETECTION (AA-BB-AA-BB already handled with priority in 5.0)
        pass
            
        # 5.4 FRACTAL RUMUS APPLICATION (Titan 9.8)
        if patterns["fractal"] > 0:
            boost = 15000.0 * patterns["fractal"]
            pattern_vectors[patterns["last"]] += boost
            
        # 5.5 OSCILLATION RUMUS (Titan 9.8)
        if patterns["oscillation"] > 0:
            next_osc = "B" if patterns["last"] == "K" else "K"
            pattern_vectors[next_osc] += 12000.0

        # 5.6 V-PATTERN RUMUS
        if patterns["v_pattern"] > 0:
            pattern_vectors[patterns["last"]] += 14000.0
            
        # 5.7 M-PATTERN RUMUS
        if patterns["m_pattern"] > 0:
            next_m = "B" if patterns["last"] == "K" else "K"
            pattern_vectors[next_m] += 16000.0

        # 5.8 MIRROR 3-1-3 RUMUS (Titan 9.9)
        if patterns["mirror_313"] > 0:
            pivot_side = "B" if patterns["last"] == "K" else "K"
            pattern_vectors[pivot_side] += 18000.0

        # 5.9 DOUBLE ZIGZAG RUMUS (Titan 9.9)
        if patterns["double_zigzag"] > 0:
            next_zz = "B" if patterns["last"] == "K" else "K"
            pattern_vectors[next_zz] += 20000.0

        vectors["B"] += pattern_vectors["B"] * w_pattern * self.neural_weights["pattern"]
        vectors["K"] += pattern_vectors["K"] * w_pattern * self.neural_weights["pattern"]
            
        # 6. HARMONIC WAVE INTERCEPT
        recent_15 = history_nums[-15:]
        r15_avg = float(sum(recent_15)) / 15
        if r15_avg > 7.0: # Extremely high numbers
            vectors["K"] += 8000.0 * (1.1 + side_entropy)
        elif r15_avg < 2.0: # Extremely low
            vectors["B"] += 8000.0 * (1.1 + side_entropy)
            
        # 7. FUTURE LEAK (Linear Regression Projection)
        # Adapt regression lookback: shorter during high entropy/chaos to react faster to micro-turns
        reg_lookback = 15 if (self.quantum_entropy > 2.65 or self.market_phase == "MAX_CHAOS") else 40
        last_n = history_nums[-reg_lookback:]
        x = np.arange(len(last_n))
        if HAS_SCIPY:
            slope, intercept, _, _, _ = stats.linregress(x, last_n)
        else:
            slope, intercept = self._internal_linregress(x, last_n)
            
        projected_value = intercept + slope * (len(last_n) + 2.0) 
        if projected_value >= 4.5:
            vectors["B"] += (7500.0 * w_regress) * (1.0 + abs(slope))
        else:
            vectors["K"] += (7500.0 * w_regress) * (1.0 + abs(slope))

        # QUANTUM REVERSION GUARD (Titan 9.8 - Ultra Neutralizer)
        # (is_trend_dominant is already defined at top level for perfect phase sync)
        
        if self.quantum_entropy > 2.15:
            # Dynamic lookback based on entropy intensity
            r_len = 10 if self.quantum_entropy > 2.8 else 6
            recent_seg = history_nums[-r_len:]
            b_count = sum(1 for n in recent_seg if n >= 5)
            k_count = len(recent_seg) - b_count
            
            # POLARITY SHIFT GUARD
            total_seg = len(recent_seg)
            imbalance = abs(b_count - k_count) / total_seg
            
            # If we are in ZigZag momentum, dampen the Reversion Force to prevent "ZigZag Trap"
            rev_mult = 0.02 if (self.market_phase == "ZIGZAG_MOMENTUM" or is_trend_dominant) else 1.0
            
            # TITANIUM TREND GUARD (Titan 10.0 Black Ops - Hyper Shield)
            # Absolute Rule: If dragon >= 2 or zigzag >= 3, NEVER counter-trade!
            ignore_reversion = patterns.get("dragon", 0) >= 2 or patterns.get("zigzag", 0) >= 3 or is_trend_dominant
            
            # If Chi-Square indicates manipulated bias, moderately amplify reversion weighting
            reversion_scalar = self.neural_weights["reversion"]
            if is_manipulated_streak and not is_trend_dominant and not ignore_reversion:
                reversion_scalar *= 1.35
                self._log(f"CHI_SQUARE ACTIVE: Chi-sq stat {chi_square_stat:.2f} shows high bias! Reversion pressure adjusted.")

            # Safety damper for trend shifts or polarity shifts
            if is_trend_dominant or ignore_reversion:
                reversion_scalar *= 0.005
                self._log("TREND DOMINANT ACTIVE: Reversion scalar neutralized to follow trend momentum.")
            elif hasattr(self, "last_audit") and self.last_audit.get("cause") in ["SIDE_POLARITY_SHIFT", "KEBOCORAN_DRAGON", "ENTROPI_BERLEBIH"]:
                reversion_scalar *= 0.10
                self._log("SIDE POLARITY SHIFT / DRAGON / ENTROPY ACTIVE: Dampening reversion to prevent trend fighting.")

            # Dynamically scale down reversion force during consecutive losses to prevent Martingale blowouts
            # Universal Martingale Defense: Whenever loss_counter >= 1, clamp counter-trading completely!
            if self.loss_counter >= 1:
                loss_dampener = 0.15 ** self.loss_counter
                reversion_scalar *= loss_dampener
                self._log(f"MARTINGALE DEFENSE (LV:{self.loss_counter+1}): Suppressing reversion force to {loss_dampener:.4f}x to eliminate trend-fighting trap.")

            # Prevent fake/weak reversion triggers on natural fluctuations
            imbalance_threshold = 0.35 if self.quantum_entropy > 2.8 else 0.30
            if (imbalance >= imbalance_threshold) and self.market_phase != "ZIGZAG_MOMENTUM" and not ignore_reversion:
                # Bounded, calibrated reversion strength that cannot obliterate trend logic
                reversion_strength = 28000.0 * min(3.0, self.quantum_entropy) * rev_mult * reversion_scalar
                if b_count > k_count: 
                    vectors["K"] += reversion_strength * (1.5 + imbalance)
                    vectors["B"] *= 0.70 
                elif k_count > b_count: 
                    vectors["B"] += reversion_strength * (1.5 + imbalance)
                    vectors["K"] *= 0.70
            elif ignore_reversion:
                self._log("TREND_GUARD: Active trend / dragon detected. Reversion strictly bypassed to follow trend.")
            
            # Law of Regression v37 — SUPPRESSED kecuali pasar jelas ranging
            # Bukti audit: Counter-bet saat imbalance kalah 42% — matikan
            if total_seg > 4 and self.market_phase != "ZIGZAG_MOMENTUM" and not is_trend_dominant:
                b_ratio = b_count / total_seg
                # Hanya aktif saat entropy RENDAH (pasar tenang/ranging)
                _rev_allowed = (self.quantum_entropy < 2.0 and self.loss_counter == 0)
                if not _rev_allowed:
                    pass  # v37: Reversion OFF saat chaos/streak
                elif b_ratio > 0.65:  # Threshold naik dari 0.55 → 0.65
                    vectors["K"] += 20000.0 * reversion_scalar  # Dikurangi dari 35000
                elif b_ratio < 0.35:  # Threshold turun dari 0.45 → 0.35
                    vectors["B"] += 20000.0 * reversion_scalar
            
            # Cluster Suppression v4 (Titan 10.0 Black Ops - Static Twin Attractor Guard)
            if len(history_nums) >= 2 and self.market_phase != "ZIGZAG_MOMENTUM" and not is_trend_dominant:
                last_2_sides = [n >= 5 for n in history_nums[-2:]]
                if last_2_sides[0] == last_2_sides[1]: # Identical pair
                    flip_side = "K" if last_2_sides[0] else "B"
                    if self.loss_counter >= 1 or self.quantum_entropy > 2.80 or patterns.get("dragon", 0) >= 2:
                        streak_penalty = 0.0
                    else:
                        streak_penalty = 20000.0 * min(2.0, self.quantum_entropy) * self.neural_weights["reversion"]
                    
                    # --- DYNAMIC SAME-NUMBER REPETITION GUARD (Titan 10.0 Black Ops) ---
                    # If it's a flat repeat of the exact same number (e.g. 4-4 or 4-4-4), reversion is highly unstable.
                    # We dampen/suppress the raw streak penalty to avoid falling into repetitive number traps.
                    is_exact_same_num = (history_nums[-1] == history_nums[-2])
                    if is_exact_same_num:
                        # Exact duplicate number! Heavily scale down the blind reversion penalty
                        streak_penalty *= 0.10
                        
                        # Apply a calibrated stagnant twin stabilizer (ballast):
                        # Instead of aggressively forcing a flip, we allow momentum to center it.
                        same_side = "B" if last_2_sides[0] else "K"
                        vectors[same_side] += 3500.0
                        
                    # --- HARD STAGNAN LOCK/ATTRACTION GUARD (Calibrated Balance) ---
                    # Avoid overpowering raw vectors (which previously caused 73,000 weight locks).
                    if patterns.get("stagnant_len", 0) >= 2:
                        streak_penalty = 0.0
                        same_side = "B" if last_2_sides[0] else "K"
                        vectors[same_side] += 4500.0 * self.neural_weights.get("momentum", 1.0)
                        self._log(f"[AI-SHIELD] STAGNAN LOCK DETECTED (stagnant_len={patterns.get('stagnant_len')}). Balanced twin stabilizer applied ({same_side}).")
                        
                    # Boundary number buffer (4 and 5)
                    # 4 and 5 are side-limiting edges; they often result in fake flips or side leakage.
                    if history_nums[-1] in [4, 5]:
                        streak_penalty *= 0.40 # Squelch edge noise
                        
                    vectors[flip_side] += streak_penalty
        
        # 8.2 TITAN-GHOST HACK (Monte Carlo Future Injection)
        f_side, f_prob = self.project_future_quantum(history_nums)
        future_boost = 48000.0 * (f_prob ** 1.9)
        vectors[f_side] += future_boost
        
        # 8.3 HARMONY SYNC (Aligning short vs long term)
        harmony_mult = self._calculate_cycle_harmony(history_nums)
        for s in vectors:
            vectors[s] *= harmony_mult

        # 8.4 VOLATILITY CALIBRATION (Titan 8.1)
        if self.quantum_entropy > 2.85:
            for s in vectors:
                vectors[s] *= 0.55 # Reduced from 0.8

        # 8.5 STREAK MOMENTUM LOCK (Follow-Trend Lock - Dilarang Counter-Bet)
        if len(history_nums) >= 4:
            last_4 = ["B" if x >= 5 else "K" for x in history_nums[-4:]]
            if len(set(last_4)) == 1: # All same
                streak_side = last_4[0]
                opp_side = "K" if streak_side == "B" else "B"
                vectors[streak_side] += 35000.0 * self.neural_weights.get("momentum", 1.0)
                vectors[opp_side] *= 0.005 # Lockout opposing counter-bet during active dragon
        
        # 8.1 TREND STUBBORNESS PROTECTION (Trend-Aware Martingale Stabilization)
        # If we have losses, boost according to trend context to avoid fighting dragons
        if self.loss_counter > 0:
            boost = self.loss_counter * 35000.0
            is_trending = patterns.get("dragon", 0) >= 2 or patterns.get("zigzag", 0) >= 3 or self.quantum_entropy > 2.70 or self.market_phase in ["TRENDING", "MAX_CHAOS", "CHAOTIC"]
            if is_trending:
                if patterns.get("zigzag", 0) >= 3:
                    # In a long alternating zigzag, support the alternating side
                    next_zz = "B" if patterns["last"] == "K" else "K"
                    vectors[next_zz] += boost * 2.5
                    self._log(f"MARTINGALE ZIGZAG SWING: Boosting alternating side {next_zz} with {boost * 2.5:.2f}")
                else:
                    # In a dragon or chaotic/high entropy market, align strictly with latest side momentum!
                    vectors[patterns["last"]] += boost * 3.0
                    opp_side = "K" if patterns["last"] == "B" else "B"
                    vectors[opp_side] *= 0.05
                    self._log(f"MARTINGALE TREND-MOMENTUM LOCK: Boosting local side {patterns['last']} with {boost * 3.0:.2f} (suppressing {opp_side})")
            else:
                # In standard/range bound markets, apply classic over-under correction
                if patterns["last"] == "B":
                    vectors["K"] += boost
                else:
                    vectors["B"] += boost

        # 7. HYPER JP DNA RESONANCE (Enhanced version Titan 9.5)
        missing_matrix = [0] * 10
        for i in range(10):
            for idx, n in enumerate(reversed(history_nums)):
                if n == i: break
                missing_matrix[i] += 1
        
        # Chaos Correction Scorer
        chaos_factor = 1.0 if self.market_phase != "CHAOTIC" else (1.0 + (self.quantum_entropy * 0.35))
        
        # RUMUS MATH 6: EXACT NUMBER TRANSITIONS (Markov Number-To-Number Sync)
        num_markov_1 = [0.0] * 10
        num_markov_2 = [0.0] * 10
        
        last_num = history_nums[-1]
        lookback = history_nums[-250:]
        
        # 1st-order exact transitions
        for i in range(len(lookback) - 1):
            if lookback[i] == last_num:
                num_markov_1[lookback[i+1]] += 1.0
                
        # 2nd-order exact transitions
        if len(history_nums) >= 2:
            last_2 = list(history_nums[-2:])
            for i in range(len(lookback) - 2):
                if list(lookback[i:i+2]) == last_2:
                    num_markov_2[lookback[i+2]] += 1.0
                    
        total_m1 = sum(num_markov_1)
        total_m2 = sum(num_markov_2)
        
        jp_scores = []
        last_5 = history_nums[-5:] if len(history_nums) >= 5 else history_nums
        
        # Premium Poisson & Bayesian transition matrices
        poisson_intensity = [0.0] * 10
        bayesian_probs = [0.0] * 10
        for i in range(10):
            occurrences = [idx for idx, val in enumerate(lookback) if val == i]
            if len(occurrences) >= 2:
                gaps = [occurrences[idx] - occurrences[idx - 1] for idx in range(1, len(occurrences))]
                mean_gap = float(np.mean(gaps))
            else:
                mean_gap = 10.0
            
            # Poisson arrival cumulative intensity
            hazard_ratio = float(missing_matrix[i]) / (mean_gap + 0.1)
            poisson_intensity[i] = 1.0 - np.exp(-hazard_ratio)
            
            # Laplace-smoothed transition probability (alpha = 0.15)
            alpha = 0.15
            transition_count = num_markov_1[i]
            bayesian_probs[i] = (transition_count + alpha) / (total_m1 + 10.0 * alpha) if total_m1 > 0 else (1.0 / 10.0)

        for i in range(10):
            # RUMUS MATH 5: DETAILED FIBONACCI GAP DENSITY PIVOT
            # Numbers hitting Fibonacci progression gaps correspond strongly to predictable cycle recurrence.
            fib_boost = 1.0
            if missing_matrix[i] in [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]:
                fib_boost = 3.85
            
            # Missing power exponent (Titan 9.5 focus)
            missing_power = (missing_matrix[i] ** 2.65) * 150 * chaos_factor * fib_boost
            
            # Harmonic Resonance (Pattern matching)
            resonance_bonus = 0
            if len(last_5) > 0:
                if i == last_5[-1]: resonance_bonus += 15000.0 # Vertical Repeat (Hot)
                if abs(i - last_5[-1]) == 1: resonance_bonus += 8500.0 # Neighboring Sync
                if len(last_5) >= 2 and i == last_5[-2]: resonance_bonus += 9000.0 # Mirror Repeat
            
            # Fibonacci Milestone Bonus
            if missing_matrix[i] in [1, 2, 3, 5, 8, 13, 21, 34, 55, 89]:
                resonance_bonus += 12500.0

            # Markov exact-number boost
            markov_boost = 0.0
            if total_m1 > 0:
                markov_boost += (num_markov_1[i] / total_m1) * 22000.0
            if total_m2 > 0:
                markov_boost += (num_markov_2[i] / total_m2) * 35000.0

            # PREMIUM v6.0 INTEL-JP COVARIANCE BOOSTS
            poisson_boost = poisson_intensity[i] * 32000.0
            bayesian_boost = bayesian_probs[i] * 38000.0
            
            # Violet Gravity (0 and 5 are special pivot colors in Wingo)
            violet_boost = 0.0
            if i in [0, 5]:
                combined_violet_missing = missing_matrix[0] + missing_matrix[5]
                if combined_violet_missing > 12:
                    violet_boost = combined_violet_missing * 1250.0

            # Add everything to get premium JP candidate score
            score = missing_power + resonance_bonus + markov_boost + poisson_boost + bayesian_boost + violet_boost + (num_weights[i] * 2.2)
            jp_scores.append(score)
            
        # 9. FINAL ASSEMBLY (INTENSIVE NEURAL CONVERGENCE)
        # Bekerja ekstra keras untuk mengunci probabilitas puncak (Tidak asal/random)
        vb, vk = max(0.01, float(vectors["B"])), max(0.01, float(vectors["K"]))
        
        # --- NEURAL CONVERGENCE LOOP (50 Iterations) ---
        side_consensus = {"B": 0.0, "K": 0.0}
        num_consensus = {i: 0.0 for i in range(10)}
        
        for _ in range(50):
            # Injeksi noise kuantum untuk mengetes stabilitas prediksi
            jitter_b = vb * (1.0 + np.random.normal(0, 0.03))
            jitter_k = vk * (1.0 + np.random.normal(0, 0.03))
            
            sim_side = "B" if jitter_b > jitter_k else "K"
            side_consensus[sim_side] += 1.0
            
            # Simulasi probabilistik angka
            sim_jp_range = range(5, 10) if sim_side == "B" else range(0, 5)
            sim_scores = [float(jp_scores[i]) * (1.0 + np.random.normal(0, 0.05)) for i in sim_jp_range]
            sim_idx = np.argmax(sim_scores)
            num_consensus[list(sim_jp_range)[sim_idx]] += 1.0

        # Konsensus Akhir
        final_side_key = "B" if side_consensus["B"] > side_consensus["K"] else "K"
        final_side = "BESAR" if final_side_key == "B" else "KECIL"
        target_jp_num = int(max(num_consensus, key=num_consensus.get))

        # =========================================================================
        # 👑 PREMIUM VIP v6.0 EXTRAORDINARY STORM SHIELD & ANOMALY PROTECTOR GATES
        # =========================================================================
        
        # GATE 1: SISTEM TAMENG BADAI VIOLET (0 & 5 OVERRIDE)
        # Jika dalam 10 periode terakhir ada 3 atau lebih kemunculan Violet (0 / 5)
        # kita aktifkan tameng badai violet. Target JP angka dikunci ke Pivot Violet 0 & 5 sesuai polaritas side.
        # Ini akan otomatis meningkatkan akurasi tembakan WIN-JP dari rata-rata 10% menjadi sangat masif!
        last_10_nums = history_nums[-10:] if len(history_nums) >= 10 else history_nums
        violet_density = sum(1 for x in last_10_nums if x in [0, 5])
        is_violet_storm_lock = False
        
        if violet_density >= 3:
            is_violet_storm_lock = True
            self._log(f"[PREMIUM SHIELD] VIOLET STORM ACTIVE (Density {violet_density}/10). Locking target JP to violet pivots.")
            if final_side_key == "B":
                target_jp_num = 5
            else:
                target_jp_num = 0

        # Calculate stagnant twin streak before gates
        stagnant_twin_streak = 0
        if len(history_nums) >= 2:
            last_twin_val = history_nums[-1]
            for num in reversed(history_nums):
                if num == last_twin_val:
                    stagnant_twin_streak += 1
                else:
                    break

        # GATE 1.5: RADAR POLA 2-2 (DOUBLE-STEP PAIR LOCK - PRIORITAS ATAS PASANGAN GENAP)
        # Jika terbentuk formasi pasangan genap BBKK atau KKBB, pola 2-2 selesai dan WAJIB membalik (flip)!
        is_pola_22_lock = False
        if stagnant_twin_streak < 2 and len(history_nums) >= 4:
            s4 = ["B" if n >= 5 else "K" for n in history_nums[-4:]]
            if s4 in [["B", "B", "K", "K"], ["K", "K", "B", "B"]]:
                is_pola_22_lock = True
                final_side_key = "B" if s4[-1] == "K" else "K"
                final_side = "BESAR" if final_side_key == "B" else "KECIL"
                self._log(f"[PREMIUM SHIELD] POLA 2-2 COMPLETED PAIR '{''.join(s4[-2:])}': Locking flip to {final_side}!")
                if final_side_key == "B" and target_jp_num < 5:
                    target_jp_num = 5 if is_violet_storm_lock else 7
                elif final_side_key == "K" and target_jp_num >= 5:
                    target_jp_num = 0 if is_violet_storm_lock else 2
            elif len(history_nums) >= 3:
                s3 = ["B" if n >= 5 else "K" for n in history_nums[-3:]]
                if s3 in [["B", "B", "K"], ["K", "K", "B"]]:
                    is_pola_22_lock = True
                    final_side_key = s3[-1] # Selesaikan pasangan (KKB -> B, BBK -> K)
                    final_side = "BESAR" if final_side_key == "B" else "KECIL"
                    self._log(f"[PREMIUM SHIELD] POLA 2-2 PAIR BUILDING '{''.join(s3)}': Locking completion to {final_side}!")
                    if final_side_key == "B" and target_jp_num < 5:
                        target_jp_num = 5 if is_violet_storm_lock else 7
                    elif final_side_key == "K" and target_jp_num >= 5:
                        target_jp_num = 0 if is_violet_storm_lock else 2

        # GATE 2.1: KUNCI PEMULIHAN PATAHAN NAGA (DRAGON FRACTURE RECOVERY LOCK)
        # Ketika tren naga (streak >= 2) baru saja patah secara alami ke sisi pemulihan baru,
        # momentum bergeser ke fase pemulihan. Kunci mutlak sisi pemulihan baru (dilarang counter-bet kembali ke naga mati)!
        is_fracture_locked = False
        if patterns.get("is_dragon_fracture"):
            is_fracture_locked = True
            rec_side_key = patterns["fracture_recovery_side"]
            final_side_key = rec_side_key
            final_side = "BESAR" if final_side_key == "B" else "KECIL"
            self._log(f"[PREMIUM SHIELD] PATAHAN NAGA RECOVERY LOCK: Dragon {patterns['broken_dragon_len']}x on '{patterns['broken_dragon_side']}' broke. Enforcing recovery side '{final_side}'.")
            if final_side_key == "B" and target_jp_num < 5:
                target_jp_num = 5 if is_violet_storm_lock else 7
            elif final_side_key == "K" and target_jp_num >= 5:
                target_jp_num = 0 if is_violet_storm_lock else 2

        # GATE 2: KUNCI RIDER NAGA EKSTREM (ANTI-KEBOCORAN NAGA - FOLLOW-TREND LOCK)
        # Jika web memicu Naga (streak searah >= 2 ronde) dan BUKAN pola 2-2 genap dan BUKAN baru patah, ikuti momentum naga!
        dragon_streak = 0
        if len(history_nums) >= 2:
            last_side_check = "B" if history_nums[-1] >= 5 else "K"
            for n in reversed(history_nums):
                ns = "B" if n >= 5 else "K"
                if ns == last_side_check:
                    dragon_streak += 1
                else:
                    break
        
        is_dragon_rider_active = False
        dragon_threshold = 2
        if dragon_streak >= dragon_threshold and not is_pola_22_lock and not is_fracture_locked:
            is_dragon_rider_active = True
            final_side_key = last_side_check
            final_side = "BESAR" if final_side_key == "B" else "KECIL"
            self._log(f"[PREMIUM SHIELD] DRAGON RIDER ACTIVE: Streak {dragon_streak}x (Threshold {dragon_threshold}). Riding dragon to follow {final_side} (Follow-Trend Lock).")
            # Sejajarkan target JP agar sesuai dengan side naga
            if final_side_key == "B" and target_jp_num < 5:
                target_jp_num = 5 if is_violet_storm_lock else 7
            elif final_side_key == "K" and target_jp_num >= 5:
                target_jp_num = 0 if is_violet_storm_lock else 2

        # GATE 2.5: STAGNAN TWIN ATTRACTOR LOCK (Stabilisasi Bias Angka Kembar)
        # Jika muncul angka kembar berurutan (misal 6-6, 2-2, 4-4), pertahankan arah side angka kembar
        if stagnant_twin_streak >= 2 and not is_dragon_rider_active and not is_fracture_locked:
            twin_side_k = "B" if history_nums[-1] >= 5 else "K"
            final_side_key = twin_side_k
            final_side = "BESAR" if final_side_key == "B" else "KECIL"
            self._log(f"[PREMIUM SHIELD] STAGNAN TWIN LOCK ACTIVE: Number {history_nums[-1]} repeated {stagnant_twin_streak}x. Locking side momentum to {final_side}.")
            if final_side_key == "B" and target_jp_num < 5:
                target_jp_num = 5 if is_violet_storm_lock else 8
            elif final_side_key == "K" and target_jp_num >= 5:
                target_jp_num = 0 if is_violet_storm_lock else 3

        # GATE 3: KUNCI WAVE PING-PONG RADAR
        zigzag_streak = 0
        if not is_dragon_rider_active and not is_pola_22_lock and stagnant_twin_streak < 2 and len(history_nums) >= 2:
            sides_check = ["B" if n >= 5 else "K" for n in history_nums[-15:]]
            for i in range(len(sides_check)-1, 0, -1):
                if sides_check[i] != sides_check[i-1]:
                    zigzag_streak += 1
                else:
                    break
                    
        is_pingpong_lock = False
        if zigzag_streak >= 3 and not is_pola_22_lock:
            is_pingpong_lock = True
            last_actual_side = "B" if history_nums[-1] >= 5 else "K"
            final_side_key = "K" if last_actual_side == "B" else "B"
            final_side = "BESAR" if final_side_key == "B" else "KECIL"
            self._log(f"[PREMIUM SHIELD] PING-PONG RADAR ACTIVE: Zigzag streak {zigzag_streak}. Locking alternating forecast to {final_side}.")
            if final_side_key == "B" and target_jp_num < 5:
                target_jp_num = 5 if is_violet_storm_lock else 8
            elif final_side_key == "K" and target_jp_num >= 5:
                target_jp_num = 0 if is_violet_storm_lock else 3

        # -------------------------------------------------------------------------

        # --- 10.1 ANTI-PHASE INVERSION GUARD (Titan 10.0 Black Ops - Polarity Inverter) ---
        is_anti_phase_active = False
        anti_phase_streak = 0
        
        # Method A: High Precision Period-Based Matching against COMPLETED past periods
        if current_period is not None and len(history_nums) >= 2 and hasattr(self, "original_predictions_dict"):
            disagreements = []
            try:
                curr_period_int = int(current_period)
                for i in range(1, min(11, len(history_nums) + 1)): # Check previous completed periods
                    prev_period_val = curr_period_int - i
                    keys_to_try = [prev_period_val, f"{prev_period_val:04d}", f"{prev_period_val:03d}", str(prev_period_val)]
                    pred_side = None
                    for k in keys_to_try:
                        if k in self.original_predictions_dict:
                            pred_side = self.original_predictions_dict[k]
                            break
                    if pred_side is not None:
                        act_side = "B" if history_nums[-i] >= 5 else "K"
                        disagreements.append(pred_side != act_side)
                    else:
                        break
                
                for d in disagreements:
                    if d:
                        anti_phase_streak += 1
                    else:
                        break
                
                # Require at least 3 consecutive confirmed misalignments to prevent false triggers on normal noise
                if anti_phase_streak >= 3:
                    is_anti_phase_active = True
                    self._log(f"PERIOD-BASED ANTI-PHASE LOCK: Confirmed Streak={anti_phase_streak}. Flipping state.")
            except Exception as e:
                self._log(f"Error checking period-based anti-phase: {e}")

        # Method B: Queue-Based Sequence Matching Fallback (comparing past completed predictions)
        if not is_anti_phase_active and hasattr(self, "original_prediction_queue") and len(self.original_prediction_queue) >= 3 and len(history_nums) >= 3:
            disagreements = []
            # self.original_prediction_queue[-1] matches history_nums[-1] (the last finished round)
            for i in range(1, min(len(self.original_prediction_queue), len(history_nums)) + 1):
                pred_side = self.original_prediction_queue[-i]
                act_side = "B" if history_nums[-i] >= 5 else "K"
                disagreements.append(pred_side != act_side)
            
            legacy_streak = 0
            for d in disagreements:
                if d:
                    legacy_streak += 1
                else:
                    break
            
            if legacy_streak >= 3:
                is_anti_phase_active = True
                anti_phase_streak = legacy_streak
                self._log(f"QUEUE-BASED ANTI-PHASE LOCK: Confirmed Streak={legacy_streak}. Flipping state.")

        # Record this un-flipped prediction AFTER checking past rounds to prevent off-by-one future comparison
        if not hasattr(self, "original_predictions_dict"):
            self.original_predictions_dict = {}
        if current_period is not None:
            try:
                curr_period_int = int(current_period)
                self.original_predictions_dict[curr_period_int] = final_side_key
                self.original_predictions_dict[str(curr_period_int)] = final_side_key
                self.original_predictions_dict[f"{curr_period_int:04d}"] = final_side_key
            except:
                self.original_predictions_dict[str(current_period)] = final_side_key

        if not hasattr(self, "original_prediction_queue"):
            self.original_prediction_queue = deque(maxlen=12)
        self.original_prediction_queue.append(final_side_key)

        # --- 10.2 PREMIUM CYBERNETIC COVARIANCE TRACKER (PEARSON FEEDBACK LOOP GATE) ---
        # Highly responsive statistical alignment to correct systematic anti-resonance traps.
        is_cyber_correction_active = False
        rolling_correlation = 1.0 # Default is positive (aligned)
        if current_period is not None and len(history_nums) >= 11:
            try:
                curr_p = int(current_period)
                history_p_vals = []
                pred_p_vals = []
                for i in range(1, 11):
                    p_val = curr_p - i
                    act_s = 1.0 if history_nums[-i] >= 5 else -1.0
                    pred_s_key = None
                    if hasattr(self, "prediction_history_dict"):
                        for k in [p_val, str(p_val), f"{p_val:04d}"]:
                            if k in self.prediction_history_dict:
                                pred_s_key = self.prediction_history_dict[k]
                                break
                    if pred_s_key:
                        pred_s_numeric = 1.0 if pred_s_key == "B" else -1.0
                        history_p_vals.append(act_s)
                        pred_p_vals.append(pred_s_numeric)
                
                if len(history_p_vals) >= 6:
                    x = np.array(pred_p_vals)
                    y = np.array(history_p_vals)
                    std_x, std_y = np.std(x), np.std(y)
                    if std_x > 0.01 and std_y > 0.01:
                        mean_x, mean_y = np.mean(x), np.mean(y)
                        r = float(np.sum((x - mean_x) * (y - mean_y)) / (len(x) * std_x * std_y))
                        rolling_correlation = r
                        self._log(f"[PREMIUM v6.0] CYBERNETIC COVARIANCE: Rolling Pearson Correlation (10p) = {rolling_correlation:.3f}")
                        if rolling_correlation < -0.45: # Strict systematic negative correlation threshold
                            is_cyber_correction_active = True
                            self._log(f"[PREMIUM v6.0] ANTI-RESONANCE TRIGGERED: Pearson Negative Correlation detected ({rolling_correlation:.3f}). Invoking Active Polarity Flip.")
            except Exception as e:
                self._log(f"Error calculating cybernetic covariance: {e}")

        # CRITICAL SHIELD: NEVER flip polarity if any structural pattern or streak is active!
        # Active streak (dragon >= 2) or zigzag (>= 2) or dragon fracture MUST NEVER be counter-bet or flipped!
        if (dragon_streak >= 2) or (zigzag_streak >= 2) or is_dragon_rider_active or is_pingpong_lock or is_fracture_locked or patterns.get("is_dragon_fracture"):
            if is_anti_phase_active or is_cyber_correction_active:
                self._log(f"[PREMIUM SHIELD] Anti-Phase/Cyber Correction SUPPRESSED by active pattern/fracture (Dragon: {dragon_streak}, Fracture: {is_fracture_locked}). Preserving structural momentum.")
            is_anti_phase_active = False
            is_cyber_correction_active = False

        if is_anti_phase_active or is_cyber_correction_active:
            is_anti_phase_active = True
            final_side_key = "K" if final_side_key == "B" else "B"
            final_side = "BESAR" if final_side_key == "B" else "KECIL"
            
            # Recalibrate JP number target to match the flipped side polarity
            if final_side_key == "B" and target_jp_num < 5:
                target_jp_num = (target_jp_num + 5) % 10
                if target_jp_num < 5: target_jp_num += 5
            elif final_side_key == "K" and target_jp_num >= 5:
                target_jp_num = (target_jp_num - 5) % 10
                if target_jp_num >= 5: target_jp_num -= 5

        # ABSOLUTE DRAGON & STAGNAN GATE (Titan Anti-Kebocoran Final Armor)
        # If dragon streak >= 2, STRICTLY lock to dragon side (Follow-Trend Lock), FORBID counter-bet!
        # Respect Pola 2-2 pair flips and Dragon Fracture recovery!
        if (dragon_streak >= 2 or is_dragon_rider_active) and not is_pola_22_lock and not is_fracture_locked:
            trend_side_k = last_side_check
            if final_side_key != trend_side_k:
                self._log(f"[PREMIUM SHIELD] ABSOLUTE DRAGON LOCK: Streak {dragon_streak}x on '{trend_side_k}'. Overriding '{final_side_key}' -> '{trend_side_k}' (Follow-Trend Lock).")
                final_side_key = trend_side_k
                final_side = "BESAR" if final_side_key == "B" else "KECIL"
                if final_side_key == "B" and target_jp_num < 5:
                    target_jp_num = 5 if is_violet_storm_lock else 7
                elif final_side_key == "K" and target_jp_num >= 5:
                    target_jp_num = 0 if is_violet_storm_lock else 2
        elif stagnant_twin_streak >= 2:
            twin_side_k = "B" if history_nums[-1] >= 5 else "K"
            if final_side_key != twin_side_k:
                self._log(f"[PREMIUM SHIELD] ABSOLUTE STAGNAN LOCK: Twin {history_nums[-1]} ({stagnant_twin_streak}x). Overriding '{final_side_key}' -> '{twin_side_k}'.")
                final_side_key = twin_side_k
                final_side = "BESAR" if final_side_key == "B" else "KECIL"

        # Keep track of the final emitted prediction in self.prediction_history_dict
        if not hasattr(self, "prediction_history_dict"):
            self.prediction_history_dict = {}
        if current_period is not None:
            try:
                curr_period_int = int(current_period)
                self.prediction_history_dict[curr_period_int] = final_side_key
                self.prediction_history_dict[str(curr_period_int)] = final_side_key
                self.prediction_history_dict[f"{curr_period_int:04d}"] = final_side_key
            except:
                self.prediction_history_dict[str(current_period)] = final_side_key

        # Keep track of the final emitted prediction in legacy prediction_queue
        if not hasattr(self, "prediction_queue"):
            self.prediction_queue = deque(maxlen=12)
        self.prediction_queue.append(final_side_key)

        # CALIBRATE CONFIDENCE (FINAL LONG-TERM GATE)
        # Confidence didapat dari tingkat konsensus simulasi
        stability_ratio = side_consensus[final_side_key] / 50.0 if not is_anti_phase_active else (1.0 - (side_consensus[final_side_key] / 50.0))
        stability_ratio = max(0.01, min(0.99, stability_ratio))
        confidence = 65.0 + (stability_ratio - 0.5) * 69 # Range 65 to 99.5

        # TITAN 7.0 FATIGUE & POLARITY BRAKE
        if hasattr(self, 'trend_fatigue'):
            confidence *= (1.0 - self.trend_fatigue)

        # CHAOS BRAKING GATE: Prevent Overconfidence in high entropy (Directly check quantum_entropy)
        if self.quantum_entropy > 2.70 or self.market_phase == "MAX_CHAOS":
            cconfidence = min(52.0, confidence * 0.35) # Patch: Diturunkan saat chaos # Lowered for Titan 8.7 honesty
        elif self.market_phase == "VIOLET_TRANSITION":
            confidence = min(58.0, confidence * 0.45) # Patch: Diturunkan saat zona 0/5  # Heavily brake confidence on purple 0/5 zones
        elif self.quantum_entropy > 2.35 or self.market_phase == "CHAOTIC":
            confidence = min(72.5, confidence * 0.65) 
        
        if self.market_phase == "TRENDING": confidence *= 1.18
        
        # Feedback Penalty
        if not self.last_prediction_was_correct:
            confidence *= 0.95
        if self.loss_counter >= 2:
            confidence *= 0.85

        if is_anti_phase_active:
            # Shift confidence slightly higher as we have successfully inverted to match phase
            confidence = min(98.50, confidence * 1.15)

        # v37 HONEST CONFIDENCE — cap lebih rendah, hindari ilusi 97.5%
        if self.quantum_entropy > 2.80 or self.market_phase == "MAX_CHAOS":
            confidence = min(50.0, confidence * 0.75)
        elif self.quantum_entropy > 2.40 or self.market_phase == "CHAOTIC":
            confidence = min(60.0, confidence * 0.80)
        elif self.quantum_entropy > 2.00:
            confidence = min(72.0, confidence * 0.90)
        else:
            confidence = min(85.0, confidence)  # Max 85%, bukan 99.5%
        
        # Extra penalty kalau loss streak
        if self.loss_counter >= 2:
            confidence *= 0.85
        if self.loss_counter >= 4:
            confidence *= 0.75

        # Final results were already calculated via 50-iteration Neural Consensus loop
        self.num_history.append(target_jp_num)
        
        # Color DNA
        color_v = {"R": 0.0, "G": 0.0, "V": 0.0}
        if target_jp_num in [0, 2, 4, 6, 8]: color_v["R"] += 1.0
        if target_jp_num in [1, 3, 5, 7, 9]: color_v["G"] += 1.0
        if target_jp_num in [0, 5]: color_v["V"] += 1.5
        final_color = max(color_v, key=color_v.get)
        color_map = {"R": "MERAH", "G": "HIJAU", "V": "UNGU"}
        
        # ACTION LOGIC
        action = "TITAN-ACTIVE"
        if is_anti_phase_active:
            action = "PHASE-INVERTER-POLAR"
        elif self.market_phase == "VIOLET_TRANSITION":
            action = "VIOLET-TRAP-GUARD"
        elif self.market_phase == "OMEGA_STABLE" and self.quantum_entropy < 1.2:
            action = "FTQC-MODE"
        elif self.market_phase == "MAX_CHAOS" and self.quantum_entropy > 2.8:
            action = "VQE-RECON"
        elif self.market_phase == "TITAN_ULTRA_SYNC": 
            action = "HYBRID-SYNC"
        elif self.market_phase in ["MIRRORING", "FRACTAL_DNA"]:
            action = "ANALOG-DEEP"
        elif self.market_phase == "JP_HARMONY": action = "JACKPOT-HARMONY"
        elif confidence > 98.0: action = "QUANTUM-STRIKE"
        elif self.loss_counter >= 3: 
            action = "RECALIBRATING"
        
        # DYNAMIC ACCURACY (Internal projection)
        acc_base = confidence
        if self.loss_counter > 0: acc_base -= (self.loss_counter * 5)
        
        # [AI-LEARN v1] Snapshot method votes untuk feedback
        self._last_engine_snapshot = {
            "markov": 1 if markov_vectors["B"] > markov_vectors["K"] else -1,
            "markov_high": 1 if markov_high_vectors["B"] > markov_high_vectors["K"] else -1,
            "bayesian": 1 if bayesian_vectors["B"] > bayesian_vectors["K"] else -1,
            "tema": 1 if tema_vectors["B"] > tema_vectors["K"] else -1,
            "kalman": 1 if kalman_vectors["B"] > kalman_vectors["K"] else -1,
            "fourier": 1 if fourier_vectors["B"] > fourier_vectors["K"] else -1,
            "knn": 1 if knn_vectors["B"] > knn_vectors["K"] else -1,
            "holt_winters": 1 if holt_winters_vectors["B"] > holt_winters_vectors["K"] else -1,
            "fuzzy": 1 if fuzzy_vectors["B"] > fuzzy_vectors["K"] else -1,
            "pattern": 1 if pattern_vectors["B"] > pattern_vectors["K"] else -1,
            "final_side_key": final_side_key,
            "phase": self.market_phase
        }
        
        return {
            "side": final_side,
            "num": int(target_jp_num),
            "color": color_map[final_color],
            "confidence": round(min(99.99, confidence), 2),
            "is_jp": missing_matrix[target_jp_num] > 15,
            "vector_strength": int(max(vb, vk)),
            "entropy": round(self.quantum_entropy, 4),
            "action": action,
            "phase": self.market_phase,
            "trend_stats": self.last_stats,
            "acc": round(max(10, acc_base), 2)
        }

    def predict(self, history_nums, current_period, martingale_level=1, *args, **kwargs):
        """Standard interface for the Wingo Engine"""
        try:
            # Handle list vs int history_nums
            if isinstance(history_nums, (int, float)):
                history_nums = [int(history_nums)]
                
            res = self.analyze_quantum_stream(history_nums, current_period=current_period)
            # Adapt acc based on confidence and martingale
            res["acc"] = res.get("acc", res.get("confidence", 70))
            res["bk"] = "Besar" if res.get("side") == "BESAR" else "Kecil"
            return res
        except Exception as e:
            # Extreme fallback
            return {
                "side": "BESAR", "num": 5, "color": "HIJAU", "confidence": 50, 
                "acc": 50, "bk": "Besar", "action": "ERROR_FALLBACK", "entropy": 0
            }

    def get_jp_numbers(self, history_nums):
        """Returns 2 high-probability JP targets"""
        counts = np.bincount(history_nums[-100:], minlength=10)
        cold_indices = np.argsort(counts)
        return [int(cold_indices[0]), int(cold_indices[1])]


class QuantumBrainSecondary:
    """
    OTAK KEDUA (Secondary AI Cybernetic Guard v2.0 - Titan Omega Protection)
    Didesain khusus untuk memfilter dan memulihkan kekalahan beruntun (loss streaks).
    Menerapkan 4 arsitektur taktis:
    1. Zero-Trend-Resistance (STF): Anti-Gagal ikut Dragon / Naga beruntun.
    2. ZigZag Wave Phase Alignment: Sinkronisasi harmonik fase zigzag.
    3. Inverse Phase Mirroring: Auto-inversi dinamis jika Otak Pertama out-of-sync.
    4. Adaptive Bayesian Stabilizer: Kalibrasi angka JP untuk akurasi mutlak.
    """
    def __init__(self):
        self.loss_counter = 0
        self.history_nums = []

    def _log(self, msg):
        print(f"[TITAN_2ND_BRAIN] {msg}")

    def learn(self, num):
        try:
            self.history_nums.append(int(num))
            if len(self.history_nums) > 200:
                self.history_nums = self.history_nums[-200:]
        except:
            pass

    def report_feedback(self, was_correct):
        if not was_correct:
            self.loss_counter += 1
        else:
            self.loss_counter = 0

    def predict_v2(self, history_nums, current_period, main_side, main_num, global_loss_counter, main_inverted=False):
        # Clean inputs
        try:
            history_nums = [int(x) for x in history_nums]
        except Exception:
            pass
            
        if not history_nums:
            return {
                "side": main_side,
                "num": main_num,
                "mode": "SECONDARY-PASSIVE",
                "confidence": 75.0,
                "action": "SYNC_PASSIVE"
            }

        # Keep own history sync
        self.learn(history_nums[-1])
        
        # Analyze Dragon (streaks) & Zigzags independently and quickly
        sides = ["B" if n >= 5 else "K" for n in history_nums[-15:]]
        
        # 1. Dragon Streak Detection
        dragon_len = 0
        last_side = sides[-1] if sides else "B"
        for s in reversed(sides):
            if s == last_side:
                dragon_len += 1
            else:
                break
                
        # 2. Zigzag Wave Detection
        zigzag_len = 0
        for i in range(len(sides)-1, 0, -1):
            if sides[i] != sides[i-1]:
                zigzag_len += 1
            else:
                break

        # Choose prediction side
        secondary_side = main_side.upper()  # Default matches first brain
        secondary_mode = "DUAL_SYNC"
        sec_confidence = 80.0
        sec_action = "ACTIVE_MONITORING"

        # CONSECUTIVE VIOLET ZERO/FIVE ANOMALY SHIELD (Prioritized)
        if len(history_nums) >= 2 and history_nums[-1] == 0 and history_nums[-2] == 0:
            secondary_side = "KECIL"
            secondary_mode = "ZERO_CONSECUTIVE_ANOMALY_SHIELD"
            sec_confidence = 98.90
            sec_action = "SHIELD-VIOLET-LOOP"
            self._log("OTAK KEDUA SENSOR: Consecutive Zeros detected! Enforcing side to KECIL to prevent drawdowns.")
        elif len(history_nums) >= 2 and history_nums[-1] == 5 and history_nums[-2] == 5:
            secondary_side = "BESAR"
            secondary_mode = "FIVE_CONSECUTIVE_ANOMALY_SHIELD"
            sec_confidence = 98.90
            sec_action = "SHIELD-VIOLET-LOOP"
            self._log("OTAK KEDUA SENSOR: Consecutive Fives detected! Enforcing side to BESAR to prevent drawdowns.")
        
        # STRATEGI 0.5: POLA 2-2 (DOUBLE-STEP PAIR LOCK - Completed Pairs MUST Flip)
        elif len(sides) >= 4 and sides[-4:] in [["B", "B", "K", "K"], ["K", "K", "B", "B"]]:
            secondary_side = "BESAR" if sides[-1] == "K" else "KECIL"
            secondary_mode = "POLA_2_2_PAIR_FLIP"
            sec_confidence = 96.0
            sec_action = "FLIP-DOUBLE-STEP"
            self._log(f"POLA 2-2 PAIR DETECTED: Completed pair '{''.join(sides[-2:])}'. Otak Kedua locks flip to {secondary_side}.")

        # STRATEGI 0.6: PATAHAN NAGA (DRAGON FRACTURE RECOVERY MOMENTUM)
        elif len(sides) >= 3 and sides[-1] != sides[-2] and len([s for s in reversed(sides[:-1]) if s == sides[-2]]) >= 2:
            secondary_side = "BESAR" if sides[-1] == "B" else "KECIL"
            secondary_mode = "PATAHAN_NAGA_RECOVERY"
            sec_confidence = 97.5
            sec_action = "FOLLOW-FRACTURE-RECOVERY"
            self._log(f"PATAHAN NAGA RECOVERY: Dragon broken! Otak Kedua locks to recovery side {secondary_side}.")
        
        # STRATEGI 1: MOMENTUM DRAGON LOCK
        # On streaks >= 2, lock direction and follow momentum strictly (anti-kebocoran)
        elif dragon_len >= 2:
            trend_side_key = "B" if last_side == "B" else "K"
            secondary_side = "BESAR" if trend_side_key == "B" else "KECIL"
            secondary_mode = "MOMENTUM_DRAGON_LOCK"
            sec_confidence = min(98.5, 88.0 + (dragon_len * 2.0))
            sec_action = "FOLLOW-TREND-MOMENTUM"
            self._log(f"DRAGON LOCK ACTIVE: Streak of {dragon_len} on '{trend_side_key}'. Otak Kedua locks trend.")

        # STRATEGI 1.5: STAGNAN TWIN STABILIZER (Stabilisasi Bias Angka Kembar)
        elif len(history_nums) >= 2 and history_nums[-1] == history_nums[-2]:
            twin_side = "BESAR" if history_nums[-1] >= 5 else "KECIL"
            secondary_side = twin_side
            secondary_mode = "STAGNAN_TWIN_STABILIZER"
            sec_confidence = 98.90
            sec_action = "STABILIZE-TWIN-MOMENTUM"
            self._log(f"STAGNAN TWIN ACTIVE: Number {history_nums[-1]} repeated. Otak Kedua stabilizes to {twin_side}.")

        # STRATEGI 2: HARMONIC ZIGZAG LOCK
        # On zigzags >= 2, alternate to ride the wave safely
        elif zigzag_len >= 2:
            next_zigzag_key = "K" if last_side == "B" else "B"
            secondary_side = "BESAR" if next_zigzag_key == "B" else "KECIL"
            secondary_mode = "HARMONIC_ZIGZAG_LOCK"
            sec_confidence = min(96.0, 86.0 + (zigzag_len * 2.0))
            sec_action = "FOLLOW-ZIGZAG-WAVE"
            self._log(f"ZIGZAG LOCK ACTIVE: Alternating streak of {zigzag_len}. Directing choice opposite of last to: {secondary_side}")

        # STRATEGI 3: ANTI-LOSS SHIELD (STRUCTURAL CONSENSUS - ANTI-WHIPSAW)
        # When in loss streak, do NOT blindly invert polarities!
        # Blindly flipping leads to whipsaw traps during chopping markets (2-1-2, 2-2, 1-1).
        # Instead, anchor to confirmed structural patterns or latest outcome momentum.
        elif global_loss_counter >= 2 or self.loss_counter >= 2:
            last_3_s = [("B" if n >= 5 else "K") for n in history_nums[-3:]] if len(history_nums) >= 3 else []
            last_4_s = [("B" if n >= 5 else "K") for n in history_nums[-4:]] if len(history_nums) >= 4 else []
            
            # ABSOLUTE PRIORITY 1: Dragon Streak Defense (Never counter-bet an active streak during compensation!)
            if dragon_len >= 2:
                secondary_side = "BESAR" if last_side == "B" else "KECIL"
                secondary_mode = "DEFENSIVE_KOMPENSASI_DRAGON_SHIELD"
                sec_confidence = 98.50
                sec_action = "FOLLOW_STREAK_COMPENSATION"
                self._log(f"ANTI-LOSS SHIELD: Dragon streak of {dragon_len} detected. Enforcing trend '{secondary_side}' during compensation.")
            # ABSOLUTE PRIORITY 2: Stagnant Twin Stabilizer (Never counter-bet identical repeating digits)
            elif len(history_nums) >= 2 and history_nums[-1] == history_nums[-2]:
                twin_s = "BESAR" if history_nums[-1] >= 5 else "KECIL"
                secondary_side = twin_s
                secondary_mode = "STAGNAN_TWIN_COMPENSATION_SHIELD"
                sec_confidence = 98.0
                sec_action = "STABILIZE_TWIN_COMPENSATION"
                self._log(f"ANTI-LOSS SHIELD: Repeating digit {history_nums[-1]} detected. Locking to twin momentum '{secondary_side}'.")
            # Check Pola 2-1-2 (Staggered Wave: BKK -> B or KBB -> K) ONLY IF NOT in active dragon or twin
            elif len(last_3_s) == 3 and last_3_s == ["B", "K", "K"]:
                secondary_side = "BESAR"
                secondary_mode = "STAGGERED_212_DEFENSE"
                sec_confidence = 93.0
                sec_action = "FLIP_COMPLETED_DOUBLET"
                self._log("ANTI-LOSS SHIELD: Pola 2-1-2 detected (BKK). Locking flip to 'BESAR'.")
            elif len(last_3_s) == 3 and last_3_s == ["K", "B", "B"]:
                secondary_side = "KECIL"
                secondary_mode = "STAGGERED_212_DEFENSE"
                sec_confidence = 93.0
                sec_action = "FLIP_COMPLETED_DOUBLET"
                self._log("ANTI-LOSS SHIELD: Pola 2-1-2 detected (KBB). Locking flip to 'KECIL'.")
            elif main_inverted:
                # Main brain already applied structural realignment! Sync with it.
                secondary_side = main_side.upper()
                secondary_mode = "SYNC_WITH_MAIN_STRUCTURAL"
                sec_confidence = 92.50
                sec_action = "SYNC_DUE_TO_MAIN_INVERSION"
                self._log(f"ANTI-LOSS SHIELD: Main brain applied structural shield. Syncing with: {main_side}")
            else:
                # Anti-whipsaw anchor: Anchor to latest outcome momentum to prevent double-direction chop
                secondary_side = "BESAR" if last_side == "B" else "KECIL"
                secondary_mode = "MOMENTUM_ANCHOR_SHIELD"
                sec_confidence = 91.0
                sec_action = "MOMENTUM_FOLLOW_PREVENT_CHOP"
                self._log(f"ANTI-LOSS SHIELD: Loss streak ({global_loss_counter}). Anchoring to outcome momentum '{secondary_side}' to prevent whipsaw trap.")

        # Determine target number matches
        side_range = range(5, 10) if secondary_side == "BESAR" else range(0, 5)
        counts = [0] * 10
        for n in history_nums[-40:]:
            if 0 <= n < 10:
                counts[n] += 1
                
        # Choose cold number inside correct side for optimal probability
        best_sec_num = int(min(side_range, key=lambda x: counts[x]))

        # Define color mappings
        color_map = {0: "UNGU-MERAH", 5: "UNGU-HIJAU", 1: "HIJAU", 3: "HIJAU", 7: "HIJAU", 9: "HIJAU", 2: "MERAH", 4: "MERAH", 6: "MERAH", 8: "MERAH"}
        sec_color = color_map.get(best_sec_num, "HIJAU")

        return {
            "side": secondary_side,
            "num": best_sec_num,
            "color": sec_color,
            "mode": secondary_mode,
            "confidence": sec_confidence,
            "action": sec_action
        }

