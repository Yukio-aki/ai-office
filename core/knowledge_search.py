import os
from pathlib import Path
from typing import List, Dict
import re

import os
import json
from pathlib import Path
from typing import List, Dict


class KnowledgeSearch:
    """Умный поиск по базе знаний с ранжированием"""

    def __init__(self):
        self.base_path = Path(__file__).parent.parent / "knowledge_base"
        self.index = self._load_index()

    def _load_index(self) -> Dict:
        """Загружает индекс из JSON"""
        index_file = self.base_path / "index.json"
        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"examples": [], "rules": []}

    def search_by_tech(self, tech: str, keywords: List[str], max_results: int = 2) -> List[Dict]:
        """Ищет примеры для технологии с ранжированием"""
        results = []

        for ex in self.index.get("examples", []):
            if ex["tech"] == tech:
                # Считаем релевантность
                score = 0
                ex_text = ex["description"].lower() + " " + " ".join(ex["keywords"])

                for kw in keywords:
                    if kw.lower() in ex_text:
                        score += 2
                    if kw.lower() in ex["keywords"]:
                        score += 3

                if score > 0:
                    # Загружаем содержимое файла
                    file_path = self.base_path / ex["path"]
                    if file_path.exists():
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        results.append({
                            "file": str(file_path),
                            "content": content,
                            "relevance": score,
                            "description": ex["description"]
                        })

        # Сортируем по релевантности
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:max_results]

    def get_rules(self, max_rules: int = 2) -> List[str]:
        """Возвращает правила"""
        rules = [r["content"] for r in self.index.get("rules", [])]
        return rules[:max_rules]

    def _build_index(self) -> Dict[str, List[str]]:
        """Строит простой индекс по ключевым словам"""
        index = {}

        # Проходим по всем файлам в knowledge_base
        for file_path in self.base_path.glob("**/*.*"):
            if file_path.suffix in ['.html', '.txt', '.md']:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().lower()

                    # Извлекаем ключевые слова из содержимого
                    words = set(re.findall(r'\b\w+\b', content))
                    for word in words:
                        if len(word) > 3:  # Игнорируем короткие слова
                            if word not in index:
                                index[word] = []
                            index[word].append(str(file_path))
                except:
                    continue

        return index

    def search(self, keywords: List[str], max_results: int = 2) -> List[Dict]:
        """Ищет файлы по ключевым словам"""
        results = []
        found_files = set()

        # Ищем по каждому ключевому слову
        for keyword in keywords:
            if keyword.lower() in self.index:
                for file_path in self.index[keyword.lower()]:
                    if file_path not in found_files:
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            results.append({
                                "file": file_path,
                                "content": content[:500]  # Первые 500 символов
                            })
                            found_files.add(file_path)
                        except:
                            continue

        return results[:max_results]

    def search_by_type(self, query: str, file_type: str = "html") -> List[Dict]:
        """Ищет файлы определенного типа"""
        results = []
        pattern = f"**/*.{file_type}"

        for file_path in self.base_path.glob(pattern):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Простой поиск по содержимому
                if query.lower() in content.lower():
                    results.append({
                        "file": str(file_path),
                        "content": content[:500]
                    })
            except:
                continue

        return results[:3]

    def search_with_context(self, keywords: List[str]) -> Dict:
        """Ищет примеры + правила"""
        examples = self.search(keywords, file_type="html")
        rules = self.search_by_type("", "txt")  # Все правила

        return {
            "examples": examples,
            "rules": rules[:2]  # Первые 2 правила
        }