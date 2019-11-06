use crate::{FactBase, NodeId, ToSymbol};
use clingo::*;
use std::fs::File;
use std::io::BufRead;
use std::io::BufReader;
use anyhow::Result;

#[derive(Debug, Clone)]
pub struct Profile {
    id: ProfileId,
    pub input: Vec<NodeId>,
    pub plus: Vec<NodeId>,
    pub minus: Vec<NodeId>,
    pub zero: Vec<NodeId>,
    pub notplus: Vec<NodeId>,
    pub notminus: Vec<NodeId>,
    pub min: Vec<NodeId>,
    pub max: Vec<NodeId>,
}

pub enum NodeSign {
    Plus,
    Minus,
    Zero,
    NotPlus,
    NotMinus,
}
impl ToSymbol for NodeSign {
    fn symbol(&self) -> Result<Symbol, ClingoError> {
        Ok(match self {
            NodeSign::Plus => Symbol::create_number(1),
            NodeSign::Minus => Symbol::create_number(-1),
            NodeSign::Zero => Symbol::create_number(0),
            NodeSign::NotPlus => Symbol::create_id("notPlus", true).unwrap(),
            NodeSign::NotMinus => Symbol::create_id("notMinus", true).unwrap(),
        })
    }
}
pub type ProfileId = String;

#[derive(ToSymbol)]
pub struct Input<'a> {
    profile: &'a ProfileId,
    node: &'a NodeId,
}

#[derive(ToSymbol)]
pub struct ObsVLabel<'a> {
    profile: &'a ProfileId,
    node: &'a NodeId,
    sign: NodeSign,
}

#[derive(ToSymbol)]
pub struct IsMin<'a> {
    profile: &'a ProfileId,
    node: &'a NodeId,
}

#[derive(ToSymbol)]
pub struct IsMax<'a> {
    profile: &'a ProfileId,
    node: &'a NodeId,
}

impl Profile {
    pub fn to_facts(&self) -> FactBase {
        let mut facts = FactBase::new();
        for node in &self.plus {
            facts.insert(&ObsVLabel {
                profile: &self.id,
                node,
                sign: NodeSign::Plus,
            });
        }
        for node in &self.minus {
            facts.insert(&ObsVLabel {
                profile: &self.id,
                node,
                sign: NodeSign::Minus,
            });
        }
        for node in &self.zero {
            facts.insert(&ObsVLabel {
                profile: &self.id,
                node,
                sign: NodeSign::Zero,
            });
        }
        for node in &self.notplus {
            facts.insert(&ObsVLabel {
                profile: &self.id,
                node,
                sign: NodeSign::NotPlus,
            });
        }
        for node in &self.notminus {
            facts.insert(&ObsVLabel {
                profile: &self.id,
                node,
                sign: NodeSign::NotMinus,
            });
        }
        for node in &self.input {
            facts.insert(&Input {
                profile: &self.id,
                node,
            });
        }
        for node in &self.min {
            facts.insert(&IsMin {
                profile: &self.id,
                node,
            });
        }
        for node in &self.max {
            facts.insert(&IsMax {
                profile: &self.id,
                node,
            });
        }
        facts
    }
}

pub fn read(file: &File, id: &str) -> Result<Profile> {
    let file = BufReader::new(file);
    let mut input = vec![];
    let mut plus = vec![];
    let mut minus = vec![];
    let mut zero = vec![];
    let mut notplus = vec![];
    let mut notminus = vec![];
    let mut min = vec![];
    let mut max = vec![];

    for line in file.lines() {
        let l1 = line?;
        let l = l1.trim();
        if !l.is_empty() {
            match profile::statement(&l) {
                Ok(PStatement::Input(s)) => {
                    input.push(NodeId::Or(s));
                }
                Ok(PStatement::Plus(s)) => {
                    plus.push(NodeId::Or(s));
                }
                Ok(PStatement::Minus(s)) => {
                    minus.push(NodeId::Or(s));
                }
                Ok(PStatement::Zero(s)) => {
                    zero.push(NodeId::Or(s));
                }
                Ok(PStatement::NotPlus(s)) => {
                    notplus.push(NodeId::Or(s));
                }
                Ok(PStatement::NotMinus(s)) => {
                    notminus.push(NodeId::Or(s));
                }
                Ok(PStatement::Min(s)) => {
                    min.push(NodeId::Or(s));
                }
                Ok(PStatement::Max(s)) => {
                    max.push(NodeId::Or(s));
                }
                Err(e) => println!("Parse error: {}", e),
            }
        }
    }
    Ok(Profile {
        id: id.to_string(),
        input,
        plus,
        minus,
        zero,
        notplus,
        notminus,
        min,
        max,
    })
}

#[derive(Debug, Clone)]
pub enum PStatement {
    Input(String),
    Plus(String),
    Minus(String),
    Zero(String),
    NotPlus(String),
    NotMinus(String),
    Min(String),
    Max(String),
}

peg::parser! {grammar profile() for str {
    use super::PStatement;
    use super::PStatement::Input as OtherInput;
    use super::PStatement::Plus;
    use super::PStatement::Minus;
    use super::PStatement::Zero;
    use super::PStatement::NotPlus;
    use super::PStatement::NotMinus;
    use super::PStatement::Min;
    use super::PStatement::Max;

    rule whitespace() = quiet!{[' ' | '\t']+}

    pub rule statement() -> PStatement
        = s:ident() whitespace()+ "=" whitespace()+ "input" { OtherInput(s.to_string()) }
        / s:ident() whitespace()+ "=" whitespace()+ "+" { Plus(s.to_string()) }
        / s:ident() whitespace()+ "=" whitespace()+ "-" { Minus(s.to_string()) }
        / s:ident() whitespace()+ "=" whitespace()+ "0" { Zero(s.to_string()) }
        / s:ident() whitespace()+ "=" whitespace()+ "notPlus" { NotPlus(s.to_string()) }
        / s:ident() whitespace()+ "=" whitespace()+ "notMinus" { NotMinus(s.to_string()) }
        / s:ident() whitespace()+ "=" whitespace()+ "MIN" { Min(s.to_string()) }
        / s:ident() whitespace()+ "=" whitespace()+ "MAX" { Max(s.to_string()) }

    pub rule ident() -> &'input str
        = $(['a'..='z' | 'A'..='Z' | '0'..='9' | '_' | ':' | '-' | '[' | ']']*)
}}
