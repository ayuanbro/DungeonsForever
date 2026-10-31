"""Scoped publication preserves unrelated source facts and rejects mixed builds."""
from pathlib import Path
import tempfile
import unittest
from data_pipeline.professions.build import emit_lua
from data_pipeline.professions.publish_profession import publish, read_provider
from data_pipeline.professions.model import SourceError


def record(slug, spell):
    return {'spell': spell, 'profession': slug, 'coverage': 'none',
            'missingReasons': ['learningSourceMissing'], 'routes': []}


class PublicationTests(unittest.TestCase):
    def test_selected_profession_is_replaced_and_other_professions_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target=root/'old.lua';incoming=root/'new.lua'
            old={'alchemy': {101:record('alchemy',101)},'first-aid': {1:record('first-aid',1)}}
            new={'alchemy': {102:record('alchemy',102)},'first-aid': {3275:record('first-aid',3275)}}
            meta={'build':'1.60.1.70685','fingerprint':'fixture'}
            target.write_bytes(emit_lua(old,meta));incoming.write_bytes(emit_lua(new,meta))
            before=read_provider(target.read_bytes())[0]
            publish(target,incoming,'first-aid',root/'report.json')
            after=read_provider(target.read_bytes())[0]
            self.assertEqual(after['alchemy'],before['alchemy'])
            self.assertEqual(set(after['first-aid']),{3275})
            self.assertNotIn(1,after['first-aid'])

    def test_cross_build_publication_fails_without_modifying_target(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target=root/'old.lua';incoming=root/'new.lua'
            facts={'first-aid':{3275:record('first-aid',3275)}}
            target.write_bytes(emit_lua(facts,{'build':'1.60.1.70685','fingerprint':'a'}))
            incoming.write_bytes(emit_lua(facts,{'build':'1.60.1.70532','fingerprint':'b'}))
            before=target.read_bytes()
            with self.assertRaises(SourceError):publish(target,incoming,'first-aid',root/'report.json')
            self.assertEqual(target.read_bytes(),before)


if __name__=='__main__':unittest.main()
