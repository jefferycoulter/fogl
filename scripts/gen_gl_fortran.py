import argparse
import hashlib
import re
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ElementTree, Element
from typing import Any, Dict, Set, Tuple, List

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Generate Fortran OpenGL bindings from gl.xml")
    ap.add_argument("--xml", required=True, help="Path to gl.xml")
    ap.add_argument("--version", required=True, help="Target GL version")
    ap.add_argument("--profile", default="core", choices=["core", "compatibility"])
    ap.add_argument("--api", default="gl", choices=["gl"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--strict-missing", action="store_true")
    return ap.parse_args()

def version_tuple(s: str) -> Tuple[int, int]:
    m = re.match(r"^\s*(\d+)\.(\d+)\s*$", s)
    if not m: 
        raise ValueError(f"Bad version string: {s}")
    return int(m.group(1)), int(m.group(2))

def feature_version_tuple(node: Element) -> Tuple[int, int]:
    v = node.attrib.get("number")
    return version_tuple(v) if v else None

TYPE_MAP = {
    "GLenum":     "integer(c_int)",
    "GLboolean":  "integer(c_int)",
    "GLbitfield": "integer(c_int)",
    "GLbyte":     "integer(c_signed_char)",
    "GLshort":    "integer(c_short)",
    "GLint":      "integer(c_int)",
    "GLsizei":    "integer(c_int)",
    "GLubyte":    "integer(c_signed_char)",   # by-value; pointer params map to c_ptr
    "GLushort":   "integer(c_short)",
    "GLuint":     "integer(c_int)",

    "GLfloat":    "real(c_float)",
    "GLclampf":   "real(c_float)",
    "GLdouble":   "real(c_double)",
    "GLclampd":   "real(c_double)",

    "GLintptr":   "integer(c_ptrdiff_t)",
    "GLsizeiptr": "integer(c_size_t)",

    "GLchar":     "integer(c_signed_char)",   # only if truly by-value; * -> c_ptr
    "GLvoid":     "type(c_ptr)",
    "void":       None,

    "GLint64":    "integer(c_long_long)",
    "GLuint64":   "integer(c_long_long)",     # unsigned 64 isn’t in iso_c_binding

    "GLsync":     "type(c_ptr)",
    "GLDEBUGPROC":"type(c_ptr)",
}

def collect_commands(tree: ElementTree, api: str, target_version: str, profile: str) -> Set[str]:
    root = tree.getroot()
    version = version_tuple(target_version)
    available = set()
    # loop over features and add required commands
    for feat in root.findall("./feature"):
        # skip features with non-matching API or too high version
        if feat.attrib.get("api") != api:
            continue
        feature_version = feature_version_tuple(feat)
        if feature_version is None or feature_version > version:
            continue
        for req in feat.findall("./require"):
            for cmd in req.findall("./command"):
                name = cmd.attrib.get("name")
                if name: 
                    available.add(name)
    # remove commands that are removed in this version/profile
    for feat in root.findall("./feature"):
        # skip features with non-matching API or too high version
        if feat.attrib.get("api") != api:
            continue
        feature_version = feature_version_tuple(feat)
        if feature_version is None or feature_version > version:
            continue
        for rem in feat.findall("./remove"):
            # skip if profile doesn't match
            if rem.attrib.get("profile") and rem.attrib["profile"] != profile:
                continue
            for cmd in rem.findall("./command"):
                name = cmd.attrib.get("name")
                if name and name in available:
                    available.remove(name)
    return available

def text_star_count(param_elem: Element) -> int:
    count = 0
    def add_text(t: str) -> None:
        nonlocal count
        if t:
            count += t.count('*')
    add_text(param_elem.text)
    for child in param_elem:
        add_text(child.text)
        add_text(child.tail)
    return count

def get_param_type_name(param_elem: Element) -> str:
    ptype = param_elem.find("ptype")
    if ptype is not None and ptype.text:
        return ptype.text.strip()
    txt = (param_elem.text or "")
    m = re.search(r"\b(GL\w+|void)\b", txt)
    return m.group(1) if m else "void"

def map_param_to_fortran(ptype: str, pointer_depth: int, is_return=False) -> Any:
    if is_return:
        if ptype == "void" and pointer_depth == 0:
            return ("subroutine", None)
        if pointer_depth >= 1:
            return ("function", "type(c_ptr)")
        base = TYPE_MAP.get(ptype) or "integer(c_int)"
        return ("function", base)
    if pointer_depth >= 1:
        return "type(c_ptr), value"
    base = TYPE_MAP.get(ptype) or "integer(c_int)"
    return f"{base}, value"

def sanitize_name(nm: str) -> str:
    return re.sub(r'[^A-Za-z0-9_]', '_', nm)

FORTRAN_RESERVED = {
    "abstract","allocatable","allocate","assign","associate","asynchronous","backspace","bind",
    "block","call","case","class","close","common","contains","continue","cycle","data","deallocate",
    "decode","deferred","dimension","do","else","elsewhere","encode","end","entry","enum","enumerator",
    "equivalence","exit","extends","external","final","forall","format","function","generic","goto",
    "if","implicit","import","include","inquire","intent","interface","intrinsic","len","logical","module",
    "namelist","non_overridable","none","nopass","nullify","only","open","operator","optional","parameter",
    "pass","pause","pointer","print","private","procedure","protected","public","pure","read","real",
    "recursive","result","return","rewind","save","select","sequence","stop","submodule","subroutine",
    "target","then","type","use","value","volatile","where","while","write"
}

def safe_ident(nm):
    s = sanitize_name(nm.lower())
    if s in FORTRAN_RESERVED:
        s = s + "_"
    # Fortran identifiers must start with letter; if not, prefix
    if not re.match(r"[a-z_]", s):
        s = "a_" + s
    return s

MAX_IDENT = 63  # typical compiler limit; safe for Fortran 2008
def shorten_ident(name: str, maxlen: int = MAX_IDENT) -> str:
    base = safe_ident(name)  # your reserved-word-safe, letter-leading helper
    if len(base) <= maxlen:
        return base
    # 8 hex chars + 1 underscore
    h = hashlib.sha1(base.encode("utf-8")).hexdigest()[:8]
    keep = maxlen - 9
    if keep < 1:
        # pathological; fall back to a prefix + hash
        return ("x" + h)[:maxlen]
    return f"{base[:keep]}_{h}"

def build_command_signature(cmd_elem: Element) -> Tuple[str, Tuple[str, int], List[Tuple[str, str, int]]]:
    proto = cmd_elem.find("proto")
    name = proto.find("name").text.strip()
    ret_ptype = "void"
    ret_p = proto.find("ptype")
    if ret_p is not None and ret_p.text:
        ret_ptype = ret_p.text.strip()
    ret_ptr_depth = 0
    def add_text(t: str) -> None:
        nonlocal ret_ptr_depth
        if t: 
            ret_ptr_depth += t.count('*')
    add_text(proto.text)
    for ch in proto:
        add_text(ch.text)
        add_text(ch.tail)
    params = []
    for p in cmd_elem.findall("param"):
        p_name_elem = p.find("name")
        pname = p_name_elem.text.strip() if p_name_elem is not None else "arg"
        ptype = get_param_type_name(p)
        pstars = text_star_count(p)
        params.append((pname, ptype, pstars))
    return name, (ret_ptype, ret_ptr_depth), params

def parse_enum_value(val_str: str) -> Tuple[str, str]:
    s = val_str.strip().lower()
    # strip a trailing 'u' or 'ul' etc. for parsing
    s = re.sub(r'(?<=\w)[uUlL]+$', '', s)
    n = int(s, 16) if s.startswith("0x") else int(s, 10)
    return n

def collect_enums(tree: ElementTree) -> Dict[str, Tuple[str, str]]:
    root = tree.getroot()
    enums_out = {}
    for enums in root.findall("./enums"):
        for e in enums.findall("./enum"):
            name = e.attrib.get("name")
            if not name:
                continue
            if "alias" in e.attrib:
                # skip alias entries (the aliased target will be present with a value)
                continue
            val = e.attrib.get("value")
            if val is None:
                continue
            try:
                n = parse_enum_value(val)
            except ValueError:
                # Rare oddballs: just skip if unparsable
                continue
            enums_out[name] = n
    return enums_out

def emit_fortran_module(module_name: str, 
                        functions: List, 
                        enums: Dict[str, Tuple[str, str]], 
                        strict_missing: bool) -> str:
    w = []

    w.append(f"module {module_name}")
    w.append("  use iso_c_binding")
    w.append("  implicit none")
    w.append("")
    w.append("  interface")
    w.append("     function gl_get_proc_address(name) bind(C, name=\"gl_get_proc_address\") result(p)")
    w.append("       import :: c_ptr, c_char")
    w.append("       character(kind=c_char), dimension(*) :: name")
    w.append("       type(c_ptr) :: p")
    w.append("     end function")
    w.append("  end interface")
    w.append("")
    # w.append("  private")
    w.append("  public :: glLoadFunctions")
    w.append("")

    # enums
    def boz_hex(n: int, kind: str) -> str:
        # kind is "c_int" or "c_long_long"
        width = 8 if kind == "c_int" else 16
        return f"int(Z'{n:0{width}X}', kind={kind})"
    
    w.append("  ! ---- OpenGL Enums (from gl.xml) ----")
    for nm in sorted(enums.keys()):
        n = enums[nm]
        safe = shorten_ident(nm)
        w.append(f"  ! {nm}")
        if -2_147_483_648 <= n <= 2_147_483_647:
            w.append(f"  integer(c_int), parameter :: {safe} = {n}")
        else:
            # represent large values in hex for readability
            if n < 0:
                w.append(f"  integer(c_long_long), parameter :: {safe} = {n}")
            else:
                w.append(f"  integer(c_long_long), parameter :: {safe} = {boz_hex(n, 'c_long_long')}")
    w.append("")

    # abstract interfaces
    for f in functions:
        w.append(f"  ! -- {f['name']}")
        if f["rettag"] == "subroutine":
            w.append("  abstract interface")
            w.append(f"    subroutine {f['abs_iface']}({', '.join([pn for pn,_ in f['params']])}) bind(C)")
            w.append("      import :: c_int, c_short, c_long_long, c_float, c_double, c_signed_char, c_size_t, c_ptrdiff_t, c_char, c_ptr")
            for pn, decl in f["params"]:
                w.append(f"      {decl} :: {pn}")
            w.append("    end subroutine")
            w.append("  end interface")
        else:
            w.append("  abstract interface")
            w.append(f"    function {f['abs_iface']}({', '.join([pn for pn,_ in f['params']])}) bind(C) result(res)")
            w.append("      import :: c_int, c_short, c_long_long, c_float, c_double, c_signed_char, c_size_t, c_ptrdiff_t, c_char, c_ptr")
            for pn, decl in f["params"]:
                w.append(f"      {decl} :: {pn}")
            w.append(f"      {f['retdecl']} :: res")
            w.append("    end function")
            w.append("  end interface")
        w.append("")

    # procedure pointers
    w.append("  ! Procedure pointers")
    for f in functions:
        w.append(f"  procedure({f['abs_iface']}), pointer :: {f['pname']} => null()")
    w.append("")

    # helpers + loader
    w.append("contains")
    w.append("  subroutine to_cstr(s, out)")
    w.append("    character(len=*), intent(in) :: s")
    w.append("    character(kind=c_char), allocatable, intent(out) :: out(:)")
    w.append("    integer :: n")
    w.append("    n = len_trim(s)")
    w.append("    allocate(out(0:n))")
    w.append("    if (n > 0) out(0:n-1) = transfer(s(1:n), out(0:n-1))")
    w.append("    out(n) = c_null_char")
    w.append("  end subroutine")
    w.append("")
    w.append("  subroutine glLoadFunctions()")
    w.append("    type(c_ptr)    :: p")
    w.append("    type(c_funptr) :: fp")
    w.append("    character(kind=c_char), allocatable :: nm(:)")
    for f in functions:
        w.append(f"    call to_cstr(\"{f['name']}\", nm)")
        w.append("    p  = gl_get_proc_address(nm)")
        w.append("    fp = transfer(p, fp)")
        w.append(f"    call c_f_procpointer(fp, {f['pname']})")
        if strict_missing:
            w.append(f"    if (.not. associated({f['pname']})) stop \"Missing GL symbol: {f['name']}\"")
    w.append("  end subroutine glLoadFunctions")
    w.append(f"end module {module_name}")
    return "\n".join(w)

def generate_fortran(tree: ElementTree, 
                     api: str, 
                     target_version: str, 
                     profile: str, 
                     strict_missing: bool) -> str:
    # collect commands for target version/profile
    cmds = collect_commands(tree, api, target_version, profile)
    # map name to command node
    cmd_nodes = {}
    # build a map of command names to their xml nodes
    # (to get return type, parameters, etc.)
    for c in tree.getroot().findall("./commands/command"):
        nm = c.findtext("./proto/name")
        if nm: 
            cmd_nodes[nm] = c
    functions = []
    # build fortran signatures for each command
    for nm in sorted(cmds):
        cmd = cmd_nodes.get(nm)
        if cmd is None: 
            continue
        name, (ret_ptype, ret_ptr_depth), params = build_command_signature(cmd)
        rettag, retdecl = map_param_to_fortran(ret_ptype, ret_ptr_depth, is_return=True)
        fparams = []
        for (pname, ptype, pstars) in params:
            decl = map_param_to_fortran(ptype, pstars, is_return=False)
            fparams.append((safe_ident(pname), decl))
        abs_iface = "t_" + name
        pname = "p_" + name
        functions.append({
            "name": name,
            "rettag": rettag,
            "retdecl": retdecl,
            "params": fparams,
            "abs_iface": abs_iface,
            "pname": pname
        })
    enums = collect_enums(tree)
    module_name = f"gl_bindings_{target_version.replace('.', '')}_{profile}"
    return emit_fortran_module(module_name, functions, enums, strict_missing)

def main():
    args = parse_args()
    tree = ET.parse(args.xml)
    code = generate_fortran(tree, args.api, args.version, args.profile, args.strict_missing)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Wrote {args.out}")

if __name__ == "__main__":
    main()
