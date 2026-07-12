import re
import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def copy_source_files_to_temp(temp_dir: Path):
    """Copies necessary source files to a temporary directory for isolated testing."""
    source_root = ROOT
    temp_app_dir = temp_dir / 'app'
    temp_static_dir = temp_app_dir / 'static'
    temp_static_dir.mkdir(parents=True, exist_ok=True)

    files_to_copy = [
        'app/models.py', 'app/agents.py', 'app/industry_prompts.py', 'app/seasonal.py',
        'app/static/index.html', 'app/static/client.html'
    ]
    for file_path in files_to_copy:
        source_file = source_root / file_path
        if source_file.exists():
            shutil.copy(source_file, temp_dir / file_path)


class EuroLocalizationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up a temporary directory with source files for tests."""
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.temp_root = Path(cls.temp_dir.name)
        copy_source_files_to_temp(cls.temp_root)

    @classmethod
    def tearDownClass(cls):
        """Clean up the temporary directory."""
        cls.temp_dir.cleanup()

    def read_temp_file(self, path: str) -> str:
        """Reads a file from the temporary test directory."""
        return (self.temp_root / path).read_text(encoding='utf-8')

    def test_currency_localization_is_in_place(self) -> None:
        models = self.read_temp_file('app/models.py')
        agents = self.read_temp_file('app/agents.py')
        index = self.read_temp_file('app/static/index.html')
        client = self.read_temp_file('app/static/client.html')

        self.assertIn('Daily budget in Euros (€)', models)
        self.assertIn('Daily budget must be at least €5', models)
        self.assertIn('Budget: €', agents)
        self.assertIn('Daily Budget (€)', index)
        self.assertIn('formatEuroAmount', index)
        self.assertIn('€1,245.00', index)
        self.assertIn('formatEuroAmount', client)
        self.assertIn('/api/client-dashboard', client)

    def test_industry_tones_and_triggers_are_present(self) -> None:
        prompts = self.read_temp_file('app/industry_prompts.py')
        seasonal = self.read_temp_file('app/seasonal.py')
        models = self.read_temp_file('app/models.py')
        index = self.read_temp_file('app/static/index.html')

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
        if not shutil.which("node"):
            self.skipTest('node executable not found in PATH')

        for html_path in [self.temp_root / 'app/static/index.html', self.temp_root / 'app/static/client.html']:
            text = html_path.read_text(encoding='utf-8')
            scripts = re.findall(r'<script[^>]*>(.*?)</script>', text, re.S | re.I)
            self.assertGreater(len(scripts), 0, f'No inline scripts found in {html_path}')
            for script in scripts:
                with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as tmp:
                    tmp.write(script)
                    tmp_path = Path(tmp.name)
                try:
                    result = subprocess.run(["node", '--check', str(tmp_path)], capture_output=True, text=True, check=False)
                    self.assertEqual(
                        result.returncode,
                        0,
                        msg=f'{html_path} failed node --check:\n{result.stderr}',
                    )
                finally:
                    tmp_path.unlink(missing_ok=True)


if __name__ == '__main__':
    unittest.main()
