//! OpenSheet core engine.
//!
//! The engine owns the grid, tracks which cells depend on which, and computes a
//! topological recalculation order whenever a cell changes. Agentic cells are
//! not evaluated here; the engine flags them so the host (web app) can dispatch
//! them to the agents service.

pub mod engine;

pub use engine::wasm_grid::{CellAddr, CellKind, EngineError, Grid};
