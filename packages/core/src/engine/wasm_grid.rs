// Prompt: Implement a high-performance Rust-based grid engine that manages cell
// dependencies and triggers agentic updates via WebAssembly.

use std::collections::{HashMap, HashSet, VecDeque};
use std::fmt;

use wasm_bindgen::prelude::*;

/// Zero-based (row, col) address of a cell.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct CellAddr {
    pub row: u32,
    pub col: u32,
}

impl CellAddr {
    pub fn new(row: u32, col: u32) -> Self {
        Self { row, col }
    }

    /// Parse an A1-style reference such as `B12` or `AA3`.
    pub fn parse_a1(reference: &str) -> Option<Self> {
        let reference = reference.trim().to_ascii_uppercase();
        let split = reference.find(|c: char| c.is_ascii_digit())?;
        let (letters, digits) = reference.split_at(split);
        if letters.is_empty() || !letters.chars().all(|c| c.is_ascii_uppercase()) {
            return None;
        }
        let mut col: u32 = 0;
        for c in letters.chars() {
            col = col.checked_mul(26)?.checked_add(c as u32 - 'A' as u32 + 1)?;
        }
        let row: u32 = digits.parse().ok()?;
        if row == 0 {
            return None;
        }
        Some(Self::new(row - 1, col - 1))
    }

    pub fn to_a1(self) -> String {
        let mut col = self.col + 1;
        let mut letters = Vec::new();
        while col > 0 {
            let rem = (col - 1) % 26;
            letters.push((b'A' + rem as u8) as char);
            col = (col - 1) / 26;
        }
        letters.iter().rev().collect::<String>() + &(self.row + 1).to_string()
    }
}

impl fmt::Display for CellAddr {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.to_a1())
    }
}

/// What a cell holds. Mirrors `CellContent` in packages/shared/types/spreadsheet_schema.ts.
#[derive(Debug, Clone, PartialEq)]
pub enum CellKind {
    Raw(String),
    /// A traditional formula, e.g. `=SUM(A1:A3)`.
    Formula(String),
    /// A natural-language instruction evaluated by the agents service.
    AgentPrompt(String),
}

#[derive(Debug, Clone, PartialEq)]
struct Cell {
    kind: CellKind,
    /// Last computed display value.
    value: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EngineError {
    InvalidReference(String),
    Cycle(Vec<CellAddr>),
}

impl fmt::Display for EngineError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            EngineError::InvalidReference(r) => write!(f, "invalid cell reference: {r}"),
            EngineError::Cycle(cells) => {
                let names: Vec<String> = cells.iter().map(|c| c.to_a1()).collect();
                write!(f, "circular reference involving {}", names.join(", "))
            }
        }
    }
}

impl std::error::Error for EngineError {}

/// Sparse grid plus a dependency graph.
///
/// `precedents[c]` = cells that `c` reads from.
/// `dependents[c]` = cells that read from `c` (reverse edges, used for dirty propagation).
#[derive(Debug, Default)]
pub struct Grid {
    rows: u32,
    cols: u32,
    cells: HashMap<CellAddr, Cell>,
    precedents: HashMap<CellAddr, HashSet<CellAddr>>,
    dependents: HashMap<CellAddr, HashSet<CellAddr>>,
}

impl Grid {
    pub fn new(rows: u32, cols: u32) -> Self {
        Self { rows, cols, ..Default::default() }
    }

    pub fn dimensions(&self) -> (u32, u32) {
        (self.rows, self.cols)
    }

    /// Set a cell's content and declare which cells it depends on.
    ///
    /// Returns the cells that must be recalculated, in topological order
    /// (the edited cell first). Rejects edits that would introduce a cycle.
    pub fn set_cell(
        &mut self,
        addr: CellAddr,
        kind: CellKind,
        deps: &[CellAddr],
    ) -> Result<Vec<CellAddr>, EngineError> {
        let new_deps: HashSet<CellAddr> = deps.iter().copied().collect();
        let old_deps = self.precedents.get(&addr).cloned().unwrap_or_default();
        self.rewire(addr, &old_deps, &new_deps);

        if let Err(cycle) = self.recalc_order(addr) {
            // Roll back the graph change so the engine stays consistent.
            self.rewire(addr, &new_deps, &old_deps);
            return Err(cycle);
        }

        self.cells.insert(addr, Cell { kind, value: None });
        self.recalc_order(addr)
    }

    pub fn get_kind(&self, addr: CellAddr) -> Option<&CellKind> {
        self.cells.get(&addr).map(|c| &c.kind)
    }

    pub fn get_value(&self, addr: CellAddr) -> Option<&str> {
        self.cells.get(&addr).and_then(|c| c.value.as_deref())
    }

    /// Store a computed value (from the formula evaluator or an agent result).
    pub fn set_value(&mut self, addr: CellAddr, value: impl Into<String>) {
        if let Some(cell) = self.cells.get_mut(&addr) {
            cell.value = Some(value.into());
        }
    }

    pub fn clear_cell(&mut self, addr: CellAddr) -> Vec<CellAddr> {
        let old = self.precedents.get(&addr).cloned().unwrap_or_default();
        self.rewire(addr, &old, &HashSet::new());
        self.cells.remove(&addr);
        self.recalc_order(addr).unwrap_or_default()
    }

    pub fn dependents_of(&self, addr: CellAddr) -> Vec<CellAddr> {
        let mut out: Vec<CellAddr> =
            self.dependents.get(&addr).map(|s| s.iter().copied().collect()).unwrap_or_default();
        out.sort();
        out
    }

    /// Topological order of `start` and everything downstream of it (Kahn's algorithm
    /// restricted to the affected subgraph).
    pub fn recalc_order(&self, start: CellAddr) -> Result<Vec<CellAddr>, EngineError> {
        // 1. Collect the affected subgraph via BFS over dependents.
        let mut affected: HashSet<CellAddr> = HashSet::new();
        let mut queue = VecDeque::from([start]);
        while let Some(cur) = queue.pop_front() {
            if affected.insert(cur) {
                if let Some(next) = self.dependents.get(&cur) {
                    queue.extend(next.iter().copied());
                }
            }
        }

        // 2. In-degree counted only over edges inside the affected set.
        let mut indegree: HashMap<CellAddr, usize> = affected.iter().map(|&c| (c, 0)).collect();
        for &cell in &affected {
            if let Some(next) = self.dependents.get(&cell) {
                for d in next.iter().filter(|d| affected.contains(d)) {
                    *indegree.get_mut(d).expect("affected") += 1;
                }
            }
        }

        // 3. Kahn. Sort the ready set for deterministic output.
        let mut ready: Vec<CellAddr> =
            indegree.iter().filter(|(_, &n)| n == 0).map(|(&c, _)| c).collect();
        ready.sort_by(|a, b| b.cmp(a));
        let mut order = Vec::with_capacity(affected.len());
        while let Some(cell) = ready.pop() {
            order.push(cell);
            if let Some(next) = self.dependents.get(&cell) {
                let mut newly_ready = Vec::new();
                for d in next.iter().filter(|d| affected.contains(d)) {
                    let n = indegree.get_mut(d).expect("affected");
                    *n -= 1;
                    if *n == 0 {
                        newly_ready.push(*d);
                    }
                }
                ready.extend(newly_ready);
                ready.sort_by(|a, b| b.cmp(a));
            }
        }

        if order.len() != affected.len() {
            let mut cyclic: Vec<CellAddr> =
                indegree.into_iter().filter(|(_, n)| *n > 0).map(|(c, _)| c).collect();
            cyclic.sort();
            return Err(EngineError::Cycle(cyclic));
        }
        Ok(order)
    }

    fn rewire(&mut self, addr: CellAddr, remove: &HashSet<CellAddr>, add: &HashSet<CellAddr>) {
        for p in remove {
            if let Some(set) = self.dependents.get_mut(p) {
                set.remove(&addr);
            }
        }
        for p in add {
            self.dependents.entry(*p).or_default().insert(addr);
        }
        if add.is_empty() {
            self.precedents.remove(&addr);
        } else {
            self.precedents.insert(addr, add.clone());
        }
    }
}

// ---------------------------------------------------------------------------
// WebAssembly bindings
// ---------------------------------------------------------------------------

/// JS-facing wrapper. Addresses cross the boundary as A1 strings; recalc
/// orders come back as arrays of A1 strings.
#[wasm_bindgen]
pub struct WasmGrid {
    inner: Grid,
}

#[wasm_bindgen]
impl WasmGrid {
    #[wasm_bindgen(constructor)]
    pub fn new(rows: u32, cols: u32) -> WasmGrid {
        WasmGrid { inner: Grid::new(rows, cols) }
    }

    /// `kind` is one of "raw" | "formula" | "agentPrompt"; `deps` are A1 refs.
    /// Returns the recalculation order as A1 refs.
    #[wasm_bindgen(js_name = setCell)]
    pub fn set_cell(
        &mut self,
        reference: &str,
        kind: &str,
        content: &str,
        deps: Vec<String>,
    ) -> Result<Vec<String>, JsError> {
        let addr = parse(reference)?;
        let kind = match kind {
            "raw" => CellKind::Raw(content.to_owned()),
            "formula" => CellKind::Formula(content.to_owned()),
            "agentPrompt" => CellKind::AgentPrompt(content.to_owned()),
            other => return Err(JsError::new(&format!("unknown cell kind: {other}"))),
        };
        let deps = deps.iter().map(|d| parse(d)).collect::<Result<Vec<_>, _>>()?;
        let order = self.inner.set_cell(addr, kind, &deps).map_err(|e| JsError::new(&e.to_string()))?;
        Ok(order.into_iter().map(|c| c.to_a1()).collect())
    }

    #[wasm_bindgen(js_name = setValue)]
    pub fn set_value(&mut self, reference: &str, value: &str) -> Result<(), JsError> {
        self.inner.set_value(parse(reference)?, value);
        Ok(())
    }

    #[wasm_bindgen(js_name = getValue)]
    pub fn get_value(&self, reference: &str) -> Result<Option<String>, JsError> {
        Ok(self.inner.get_value(parse(reference)?).map(str::to_owned))
    }

    /// Cells downstream of `reference` that hold agent prompts. The host should
    /// dispatch these to the agents service after a recalculation.
    #[wasm_bindgen(js_name = pendingAgentCells)]
    pub fn pending_agent_cells(&self, reference: &str) -> Result<Vec<String>, JsError> {
        let order = self.inner.recalc_order(parse(reference)?).map_err(|e| JsError::new(&e.to_string()))?;
        Ok(order
            .into_iter()
            .filter(|c| matches!(self.inner.get_kind(*c), Some(CellKind::AgentPrompt(_))))
            .map(|c| c.to_a1())
            .collect())
    }

    // TODO: evaluate(reference) -> run the formula evaluator (parser not yet implemented).
}

fn parse(reference: &str) -> Result<CellAddr, JsError> {
    CellAddr::parse_a1(reference)
        .ok_or_else(|| JsError::new(&EngineError::InvalidReference(reference.to_owned()).to_string()))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn a(r: &str) -> CellAddr {
        CellAddr::parse_a1(r).unwrap()
    }

    #[test]
    fn a1_round_trip() {
        for r in ["A1", "Z9", "AA10", "AZ1", "ZZ100"] {
            assert_eq!(a(r).to_a1(), r);
        }
        assert!(CellAddr::parse_a1("A0").is_none());
        assert!(CellAddr::parse_a1("12").is_none());
    }

    #[test]
    fn recalc_is_topological() {
        let mut g = Grid::new(100, 26);
        g.set_cell(a("A1"), CellKind::Raw("1".into()), &[]).unwrap();
        g.set_cell(a("B1"), CellKind::Formula("=A1*2".into()), &[a("A1")]).unwrap();
        g.set_cell(a("C1"), CellKind::Formula("=A1+B1".into()), &[a("A1"), a("B1")]).unwrap();
        let order = g.recalc_order(a("A1")).unwrap();
        assert_eq!(order, vec![a("A1"), a("B1"), a("C1")]);
    }

    #[test]
    fn cycles_are_rejected_and_rolled_back() {
        let mut g = Grid::new(10, 10);
        g.set_cell(a("A1"), CellKind::Formula("=B1".into()), &[a("B1")]).unwrap();
        let err = g.set_cell(a("B1"), CellKind::Formula("=A1".into()), &[a("A1")]).unwrap_err();
        assert!(matches!(err, EngineError::Cycle(_)));
        assert!(g.dependents_of(a("B1")).contains(&a("A1")));
        assert!(g.dependents_of(a("A1")).is_empty());
    }
}
