"""Generate an isolated fusion policy revision; never alter prior CB sources."""
from common import *
import difflib


def main():
    base=Path(__file__).parent/'cb_fusion.py';old=base.read_text(encoding='utf-8')
    start=old.index('def eligible_slots(');end=old.index('\n\ndef logical_slot(',start)
    text=old[:start]+'from ab_dummy_first_policy import eligible_slots\n'+old[end:]
    text=text.replace('Policy: a non-target bucket samples all unused slots while G<Y; afterwards it\nsamples unused dummy slots. The target always wins if present. The policy is a\nspecific instantiation of String ORAM\'s permitted selection, not author code.',
        'Policy: the target wins; otherwise prefer an unused dummy, using green only\nwhen none remains and the quota permits. This is a separately named protocol\nrevision, not author code and not a guarantee of strictly dummy-only reads.')
    out=base.with_name('ab_dummy_first_fusion.py');out.write_text(text,encoding='utf-8')
    base.with_name('ab_dummy_first_fusion.diff').write_text(''.join(difflib.unified_diff(
        old.splitlines(True),text.splitlines(True),fromfile=base.name,tofile=out.name)),encoding='utf-8')
    save(PACKAGE/'results/ab_dummy_first_build.json',dict(status='generated',base_sha256=sha(base),
        output_sha256=sha(out),generator_sha256=sha(__file__),policy_sha256=sha(base.with_name('ab_dummy_first_policy.py')),
        change='selection helper and descriptive docstring only; authentication, fusion, nonce allocation and commits retained'))


if __name__=='__main__':main()
