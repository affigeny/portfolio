/**
 * SorterLab core model — shared by sorterlab-simulator.html and Python tests.
 * Keep formulas in sync with sorterlab/capacity.py and sorterlab/simulation.py.
 */
(() => {
  'use strict';

  const GOAL_H = 100_000;
  const GOAL_M = GOAL_H / 60;
  const ITEMS_PER_MINUTE_PER_FEED_LINE = 150;
  const ITEMS_PER_HOUR_PER_SORT_LOOP = 30_000;
  const RHO_MIN = 0.65;
  const RHO_SLOPE = 0.12;
  const WAVE_PERIOD_MINUTES = 24;
  const NOISE_AMPLITUDE = 0.35;
  const DEFAULT_SEED = 20260823;
  const LCG_MULTIPLIER = 1_664_525;
  const LCG_INCREMENT = 1_013_904_223;
  const LCG_MODULUS = 2 ** 32;

  function directionEfficiency(k) {
    return Math.max(RHO_MIN, 1 - RHO_SLOPE * k);
  }

  function normalizeParameters(raw) {
    return {
      A: Number(raw.A),
      B: Number(raw.B),
      E: Number(raw.E),
      V: Number(raw.V),
      cycle: Number(raw.cycle),
      u: Number(raw.u),
      k: Number(raw.k),
    };
  }

  function computeCapacities(rawParams, goalH = GOAL_H) {
    const p = normalizeParameters(rawParams);
    const rho = directionEfficiency(p.k);
    const A = p.A * ITEMS_PER_MINUTE_PER_FEED_LINE * 60;
    const B = p.B * ITEMS_PER_HOUR_PER_SORT_LOOP * rho;
    const E = p.E * Math.floor(3600 / p.cycle) * p.V;
    const nodes = [
      ['Подача A', A, 'nodeA', 'feed'],
      ['Сортировка B', B, 'nodeB', 'sort'],
      ['AMR E', E, 'nodeE', 'amr'],
    ];
    nodes.sort((left, right) => left[1] - right[1]);
    const bottleneck = nodes[0];
    return {
      A,
      B,
      E,
      rho,
      min: bottleneck[1],
      bn: bottleneck,
      reservePct: (bottleneck[1] / goalH - 1) * 100,
    };
  }

  function createRng(seed = DEFAULT_SEED) {
    let state = seed >>> 0;
    return {
      next() {
        state = (state * LCG_MULTIPLIER + LCG_INCREMENT) >>> 0;
        return state / LCG_MODULUS;
      },
      get seed() {
        return state;
      },
      reset(nextSeed = DEFAULT_SEED) {
        state = nextSeed >>> 0;
      },
    };
  }

  function incomingRate(minute, goalPerMinute, unevenness, rng) {
    const wave = 1 + unevenness * Math.sin((2 * Math.PI * minute) / WAVE_PERIOD_MINUTES);
    const noise = 1 + unevenness * NOISE_AMPLITUDE * (rng.next() * 2 - 1);
    return Math.max(0, goalPerMinute * wave * noise);
  }

  function createSimulationState(seed = DEFAULT_SEED) {
    return {
      tick: 0,
      backlog: 0,
      rng: createRng(seed),
      historyFeed: [],
      historyProcessed: [],
    };
  }

  function stepSimulation(state, rawParams, goalH = GOAL_H) {
    const p = normalizeParameters(rawParams);
    const capacities = computeCapacities(p, goalH);
    const goalPerMinute = goalH / 60;
    const capPerMinute = capacities.min / 60;
    const incoming = incomingRate(state.tick, goalPerMinute, p.u, state.rng);
    const processed = Math.min(incoming + state.backlog, capPerMinute);
    state.backlog = Math.max(0, state.backlog + incoming - processed);
    state.historyFeed.push(incoming);
    state.historyProcessed.push(processed);
    const snapshot = {
      minute: state.tick,
      incoming,
      processed,
      backlog: state.backlog,
    };
    state.tick += 1;
    return { snapshot, capacities };
  }

  function runSimulation(rawParams, options = {}) {
    const {
      goalH = GOAL_H,
      seed = DEFAULT_SEED,
      minutes = 60,
    } = options;
    const state = createSimulationState(seed);
    const snapshots = [];
    let capacities = computeCapacities(rawParams, goalH);

    for (let minute = 0; minute < minutes; minute += 1) {
      const result = stepSimulation(state, rawParams, goalH);
      capacities = result.capacities;
      snapshots.push(result.snapshot);
    }

    return { capacities, snapshots, state };
  }

  function resetSimulationState(state, seed = DEFAULT_SEED) {
    state.tick = 0;
    state.backlog = 0;
    state.historyFeed.length = 0;
    state.historyProcessed.length = 0;
    state.rng.reset(seed);
  }

  globalThis.SorterLabModel = {
    GOAL_H,
    GOAL_M,
    DEFAULT_SEED,
    directionEfficiency,
    normalizeParameters,
    computeCapacities,
    createRng,
    incomingRate,
    createSimulationState,
    stepSimulation,
    runSimulation,
    resetSimulationState,
  };
})();
