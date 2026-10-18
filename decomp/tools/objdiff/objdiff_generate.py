# Adapted from https://github.com/Vatuu/silent-hill-decomp/tree/master

from pathlib import Path
from argparse import ArgumentParser
from dataclasses import dataclass, asdict
from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection
import logging
import yaml
import json
import sys
import re

@dataclass
class UnitMetadata:
    progress_categories: list[str]

@dataclass
class Unit:
    name: str
    base_path: str
    target_path: str
    metadata: UnitMetadata
    symbol_mappings: dict[str, str]

@dataclass
class ProgressCategory:
    id: str
    name: str

@dataclass
class Config:
    build_base: bool
    build_target: bool
    custom_make: str
    custom_args: list[str]
    units: list[Unit]
    progress_categories: list[ProgressCategory]


def _create_config():
    parser = ArgumentParser()
    parser.add_argument("config", type = Path)
    parser.add_argument("base_dir", type = Path)
    parser.add_argument("target_dir", type = Path)
    args = parser.parse_args()

    if not args.config.exists() or args.config.is_dir() or args.config.suffix != ".yaml":
        raise ValueError(f"The given path {args.objects} is not pointing towards a valid config.")

    with open(args.config) as stream:
        try:
            return args, yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            raise exc

def _read_symbols_from_elf(path: Path):
    addr_to_name = {}
    with open(path, 'rb') as f:
        elffile = ELFFile(f)

        for section in elffile.iter_sections():
            if not hasattr(section, 'iter_symbols'):
                continue
            for sym in section.iter_symbols():
                if sym['st_info']['type'] != 'STT_FUNC':
                    continue  # skip non-function symbols
                addr = sym['st_value']
                name = sym.name
                if addr != 0 and name:  # skip undefined/empty
                    addr_to_name[addr] = name
    return addr_to_name

def _normalize_suffixed_symbols(path: Path):
    """Scan elf for symbols with numeric suffixes, return a dictionary of non-suffix -> suffix pairs"""
    symbols = _read_symbols_from_elf(path)
    suffix_pattern = re.compile(r'\.(\d+)$')
    normalized = {}

    for name in symbols.values():
        match = suffix_pattern.search(name)
        if match:
            base_name = name[: match.start()]  # strip the .<digits> suffix
            normalized[base_name] = name

    return normalized

def _read_relocation_sites(path: Path):
    """Map each relocation site (section, offset, type) to the relocated word and the name of the target symbol"""
    sites = {}
    with open(path, 'rb') as f:
        elffile = ELFFile(f)
        symtab = elffile.get_section_by_name('.symtab')
        for section in elffile.iter_sections():
            if not isinstance(section, RelocationSection):
                continue
            relocated = elffile.get_section(section['sh_info'])
            data = relocated.data()
            for reloc in section.iter_relocations():
                symbol = symtab.get_symbol(reloc['r_info_sym'])
                if symbol['st_info']['type'] == 'STT_SECTION':
                    continue
                offset = reloc['r_offset']
                sites[(relocated.name, offset, reloc['r_info_type'])] = (data[offset:offset + 4], symbol.name)
    return sites

def _map_compiler_generated_symbols(target_path: Path, base_path: Path):
    """Pair compiler-generated base symbols (e.g. mwcc jump tables @123) with the target
    symbols that the same instructions reference, return a dictionary of target -> base names"""
    target_sites = _read_relocation_sites(target_path)
    candidates = set()
    for site, (base_word, base_name) in _read_relocation_sites(base_path).items():
        if not re.fullmatch(r'@\d+', base_name) or site not in target_sites:
            continue
        target_word, target_name = target_sites[site]
        if target_word == base_word:
            candidates.add((target_name, base_name))

    # Only keep unambiguous pairs
    target_names = [target_name for target_name, _ in candidates]
    base_names = [base_name for _, base_name in candidates]
    return {
        target_name: base_name for target_name, base_name in sorted(candidates)
        if target_names.count(target_name) == 1 and base_names.count(base_name) == 1
    }

EXCLUDED_NAMES = {"data", "rodata", "sdata", "bss"}

def _collect_objects(path: Path, config) -> list[Path]:
    ignored = config["ignored_files"]
    return [
        path for path in path.rglob("*.o")
        if not any(name in path.name for name in EXCLUDED_NAMES ) and not any(file in str(path) for file in ignored)
    ]

def _determine_categories(path: Path, target_dir: Path, config) -> tuple[UnitMetadata, str]:
    modified_path = path.relative_to(target_dir)

    categories = []
    for category in config["categories"]:
        for prefix in category["paths"]:
            if re.sub(r"\\", r"/", str(modified_path)).startswith(prefix):
                categories.append(category["id"])
    return (UnitMetadata(categories), str(modified_path))

def main():
    logging.basicConfig(level = logging.INFO)
    args, config = _create_config()
    
    expected_objects = _collect_objects(args.target_dir, config)
    
    logging.info(f"Accounting for {len(expected_objects)} objects.")
    units = []
    for file in expected_objects:
        processed_path = _determine_categories(file, args.target_dir, config)
        base_path = str(args.base_dir) + "/" + re.sub(r"\\", r"/", processed_path[1]).removesuffix(".s.o").removesuffix(".c.o") + ".c.o"
        
        # Create mappings for compiler-generated symbols in base object
        # (objdiff report supports symbol mappings since v3.7.3)
        symbol_mappings = _map_compiler_generated_symbols(file, base_path) if Path(base_path).exists() else {}

        unit = Unit(
            re.sub(r"\\", r"/", processed_path[1]).removesuffix(".s.o").removesuffix(".c.o"),
            base_path if Path(base_path).exists() else None,
            re.sub(r"\\", r"/", str(file)),
            processed_path[0],
            symbol_mappings)
        units.append(unit)
    
    categories = []
    for category in config["categories"]:
        categories.append(ProgressCategory(category["id"], category["name"]))
    
    with (Path(config["output"])).open("w") as json_file:
        json.dump(asdict(Config(False, False, "make", ["progress"], units, categories)), json_file, indent=2)

if __name__ == "__main__":
    main()
