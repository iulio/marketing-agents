import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE = r"C:\Users\Iulian\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class EuroLocalizationTests(unittest.TestCase):
    def test_currency_localization_is_in_place(self) -> None:
        models = read('app/models.py')
        agents = read('app/agents.py')
        index = read('app/static/index.html')
        client = read('app/static/client.html')

        self.assertIn('Daily budget in Euros (€)', models)
        self.assertIn('Daily budget must be at least €5', models)
        self.assertIn('Budget: €', agents)
        self.assertIn('Daily Budget (€)', index)
        self.assertIn('formatEuroAmount', index)
        self.assertIn('€1,245.00', index)
        self.assertIn('formatEuroAmount', client)
        self.assertIn('/api/client-dashboard', client)

    def test_industry_tones_and_triggers_are_present(self) -> None:
        prompts = read('app/industry_prompts.py')
        seasonal = read('app/seasonal.py')
        models = read('app/models.py')
        index = read('app/static/index.html')

        for needle in ['credit_brokering', 'insurance', 'real_estate', 'financial_advisory']:
            self.assertIn(needle, prompts)
        for needle in ['AUTHORITATIVE', 'EMPATHETIC', 'CASUAL', 'INSPIRATIONAL', 'HUMOROUS']:
            self.assertIn(needle, models)
        for needle in ['Black Friday', '1 Decembrie', 'Christmas']:
            self.assertIn(needle, seasonal)
            self.assertIn(needle, index)
        for needle in ['showLocationTutorial', 'closeLocationTutorial', 'locationTutorialModal', 'Target Location Guide']:
            self.assertIn(needle, index)

    def test_inline_scripts_validate_with_node(self) -> None:
        if not Path(NODE).exists():
            self.skipTest('Bundled node runtime not available')

        for html_path in [ROOT / 'app/static/index.html', ROOT / 'app/static/client.html']:
            text = html_path.read_text(encoding='utf-8')
            scripts = re.findall(r'<script[^>]*>(.*?)</script>', text, re.S | re.I)
            self.assertGreater(len(scripts), 0, f'No inline scripts found in {html_path}')
            for script in scripts:
                with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as tmp:
                    tmp.write(script)
                    tmp_path = Path(tmp.name)
                try:
                    result = subprocess.run([NODE, '--check', str(tmp_path)], capture_output=True, text=True)
                    self.assertEqual(
                        result.returncode,
                        0,
                        msg=f'{html_path} failed node --check:\n{result.stderr}',
                    )
                finally:
                    tmp_path.unlink(missing_ok=True)


if __name__ == '__main__':
    unittest.main()
