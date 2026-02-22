import os
import time
import json
import subprocess
import platform
from datetime import datetime
from pathlib import Path
import requests
import psutil
import cpuinfo


class SystemBenchmark:
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'system': {},
            'cpu': {},
            'memory': {},
            'disk': {},
            'ollama': {},
            'models': {},
            'recommendations': {}
        }

    def get_system_info(self):
        """Собирает информацию о системе"""
        print("📊 Сбор информации о системе...")

        self.results['system'] = {
            'os': platform.system(),
            'os_version': platform.version(),
            'processor': platform.processor(),
            'machine': platform.machine(),
            'hostname': platform.node(),
            'python_version': platform.python_version(),
        }

        cpu_info = cpuinfo.get_cpu_info()
        self.results['cpu'] = {
            'brand': cpu_info.get('brand_raw', 'Unknown'),
            'cores': psutil.cpu_count(logical=False),
            'threads': psutil.cpu_count(logical=True),
            'frequency_mhz': psutil.cpu_freq().max if psutil.cpu_freq() else 'Unknown',
            'architecture': cpu_info.get('arch', 'Unknown'),
        }

        memory = psutil.virtual_memory()
        self.results['memory'] = {
            'total_gb': round(memory.total / (1024 ** 3), 2),
            'available_gb': round(memory.available / (1024 ** 3), 2),
            'percent_used': memory.percent,
        }

        disk = psutil.disk_usage('/')
        self.results['disk'] = {
            'total_gb': round(disk.total / (1024 ** 3), 2),
            'free_gb': round(disk.free / (1024 ** 3), 2),
            'percent_used': disk.percent,
        }

        print(f"✅ Система: {self.results['system']['os']}")
        print(f"✅ CPU: {self.results['cpu']['cores']} ядер, {self.results['cpu']['threads']} потоков")
        print(f"✅ RAM: {self.results['memory']['total_gb']} GB")

    def check_ollama_status(self):
        """Проверяет статус Ollama"""
        print("\n🔄 Проверка Ollama...")

        try:
            start = time.time()
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            ping_time = time.time() - start

            if response.status_code == 200:
                models = response.json().get('models', [])
                self.results['ollama'] = {
                    'running': True,
                    'ping_ms': round(ping_time * 1000, 2),
                    'models_installed': [m.get('name') for m in models],
                    'models_count': len(models)
                }
                print(f"✅ Ollama запущена (пинг: {self.results['ollama']['ping_ms']} мс)")
                print(f"📦 Установлено моделей: {len(models)}")
                return True
        except:
            self.results['ollama'] = {
                'running': False,
                'error': 'Ollama не запущена'
            }
            print("❌ Ollama не запущена")
            return False

    def benchmark_model(self, model_name, test_prompts):
        """Тестирует производительность модели"""
        print(f"\n🔄 Тестирование модели {model_name}...")

        results = {
            'model': model_name,
            'tests': [],
            'avg_time': 0,
            'avg_tokens_per_sec': 0,
            'memory_usage': []
        }

        total_time = 0
        total_tokens = 0

        for i, prompt in enumerate(test_prompts, 1):
            print(f"  Тест {i}/{len(test_prompts)}...")

            mem_before = psutil.virtual_memory().used / (1024 ** 3)

            start = time.time()
            try:
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "num_predict": 100,
                            "temperature": 0.1
                        }
                    },
                    timeout=120
                )

                elapsed = time.time() - start

                if response.status_code == 200:
                    result = response.json()
                    tokens = result.get('eval_count', 0)
                    tokens_per_sec = tokens / elapsed if elapsed > 0 else 0

                    mem_after = psutil.virtual_memory().used / (1024 ** 3)

                    test_result = {
                        'prompt': prompt[:50] + "...",
                        'time_sec': round(elapsed, 2),
                        'tokens': tokens,
                        'tokens_per_sec': round(tokens_per_sec, 2),
                        'memory_delta_gb': round(mem_after - mem_before, 2)
                    }

                    results['tests'].append(test_result)
                    total_time += elapsed
                    total_tokens += tokens

                    print(f"    ✅ {elapsed:.1f} сек, {tokens_per_sec:.1f} токен/сек")

            except Exception as e:
                print(f"    ❌ Ошибка: {e}")
                results['tests'].append({
                    'prompt': prompt[:50],
                    'error': str(e)
                })

        if results['tests']:
            results['avg_time'] = round(total_time / len(results['tests']), 2)
            if total_tokens > 0:
                results['avg_tokens_per_sec'] = round(total_tokens / total_time, 2)

        return results

    def test_parallel_performance(self, model_name):
        """Тестирует производительность при параллельных запросах"""
        print(f"\n🔄 Тестирование параллельной работы ({model_name})...")

        results = {
            'parallel_1': 0,
            'parallel_2': 0,
            'parallel_4': 0,
            'recommended': 1
        }

        start = time.time()
        try:
            requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model_name,
                    "prompt": "Say 'test'",
                    "stream": False
                },
                timeout=30
            )
            results['parallel_1'] = time.time() - start
        except:
            results['parallel_1'] = 999

        if self.results['cpu']['threads'] >= 4:
            import threading

            def send_request():
                try:
                    requests.post(
                        "http://localhost:11434/api/generate",
                        json={
                            "model": model_name,
                            "prompt": "Say 'test'",
                            "stream": False
                        },
                        timeout=30
                    )
                except:
                    pass

            start = time.time()
            threads = []
            for _ in range(2):
                t = threading.Thread(target=send_request)
                t.start()
                threads.append(t)

            for t in threads:
                t.join(timeout=35)

            results['parallel_2'] = time.time() - start

        if results['parallel_2'] < results['parallel_1'] * 1.5:
            results['recommended'] = 2
        if results['parallel_4'] < results['parallel_1'] * 2:
            results['recommended'] = 4

        return results

    def get_recommendations(self):
        """Формирует рекомендации на основе тестов"""
        mem_gb = self.results['memory']['total_gb']
        cpu_cores = self.results['cpu']['cores']

        if mem_gb >= 32:
            self.results['recommendations']['model'] = 'llama2:13b'
        elif mem_gb >= 16:
            self.results['recommendations']['model'] = 'codellama:7b'
        elif mem_gb >= 8:
            self.results['recommendations']['model'] = 'tinyllama'
        else:
            self.results['recommendations']['model'] = 'phi3:mini'

        self.results['recommendations']['parallel'] = min(cpu_cores, 4)

        self.results['recommendations']['ollama_settings'] = {
            'OLLAMA_NUM_PARALLEL': str(min(cpu_cores, 4)),
            'OLLAMA_MAX_LOADED_MODELS': '2',
            'OLLAMA_KEEP_ALIVE': '10m',
            'OLLAMA_HOST': '0.0.0.0'
        }

        self.results['recommendations']['crewai_settings'] = {
            'temperature': '0.3',
            'max_tokens': '1000',
            'max_iter': '3',
            'cache': 'True'
        }

    def save_results(self):
        """Сохраняет результаты в файл"""
        filename = f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        report = f"""# 📊 Бенчмарк системы
**Дата:** {self.results['timestamp']}

## 🖥️ Система
- ОС: {self.results['system']['os']}
- Процессор: {self.results['cpu']['brand']}
- Ядра: {self.results['cpu']['cores']} физических, {self.results['cpu']['threads']} логических
- ОЗУ: {self.results['memory']['total_gb']} GB
- Свободно: {self.results['memory']['available_gb']} GB

## 🚀 Рекомендации

### Лучшая модель: **{self.results['recommendations']['model']}**
Параллельных запросов: **{self.results['recommendations']['parallel']}**

### Настройки Ollama:
OLLAMA_NUM_PARALLEL={self.results['recommendations']['ollama_settings']['OLLAMA_NUM_PARALLEL']}
OLLAMA_MAX_LOADED_MODELS={self.results['recommendations']['ollama_settings']['OLLAMA_MAX_LOADED_MODELS']}
OLLAMA_KEEP_ALIVE={self.results['recommendations']['ollama_settings']['OLLAMA_KEEP_ALIVE']}
OLLAMA_HOST={self.results['recommendations']['ollama_settings']['OLLAMA_HOST']}

### Настройки CrewAI:
temperature={self.results['recommendations']['crewai_settings']['temperature']}
max_tokens={self.results['recommendations']['crewai_settings']['max_tokens']}
max_iter={self.results['recommendations']['crewai_settings']['max_iter']}
cache={self.results['recommendations']['crewai_settings']['cache']}

"""

        if self.results.get('models'):
            report += "\n## 📈 Результаты тестов\n\n"
            for model, data in self.results['models'].items():
                if data.get('avg_tokens_per_sec'):
                    report += f"### {model}\n"
                    report += f"- Среднее время: {data['avg_time']} сек\n"
                    report += f"- Скорость: {data['avg_tokens_per_sec']} токен/сек\n\n"

        report_file = filename.replace('.json', '_report.md')
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n✅ Результаты сохранены:")
        print(f"   📄 JSON: {filename}")
        print(f"   📄 Отчет: {report_file}")

        return filename, report_file


def main():
    print("=" * 60)
    print("🔬 БЕНЧМАРК СИСТЕМЫ ДЛЯ AI OFFICE")
    print("=" * 60)

    benchmark = SystemBenchmark()

    benchmark.get_system_info()

    if not benchmark.check_ollama_status():
        print("\n❌ Ollama не запущена. Запустите 'ollama serve' и попробуйте снова.")
        return

    models_to_test = benchmark.results['ollama']['models_installed']

    if not models_to_test:
        print("\n❌ Нет установленных моделей. Установите хотя бы одну:")
        print("   ollama pull tinyllama")
        print("   ollama pull codellama")
        return

    test_prompts = [
        "Say 'hello'",
        "Write a Python function to calculate factorial",
        "Explain what is AI in one sentence"
    ]

    for model in models_to_test[:3]:
        print(f"\n{'=' * 40}")
        print(f"ТЕСТИРОВАНИЕ: {model}")
        print('=' * 40)

        model_results = benchmark.benchmark_model(model, test_prompts)
        benchmark.results['models'][model] = model_results

        if len(models_to_test) == 1:
            parallel_results = benchmark.test_parallel_performance(model)
            benchmark.results['parallel'] = parallel_results

    benchmark.get_recommendations()
    json_file, report_file = benchmark.save_results()

    print("\n" + "=" * 60)
    print("✅ БЕНЧМАРК ЗАВЕРШЕН")
    print("=" * 60)
    print(f"\n📊 Открыть отчет: {report_file}")


if __name__ == "__main__":
    try:
        import psutil
        import cpuinfo
    except ImportError:
        print("📦 Установка зависимостей...")
        subprocess.run(["pip", "install", "psutil", "py-cpuinfo"])
        import psutil
        import cpuinfo

    main()