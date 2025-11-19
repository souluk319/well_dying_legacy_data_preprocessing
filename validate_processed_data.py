#!/usr/bin/env python3
"""
처리된 데이터의 품질을 철저히 검증하는 스크립트
원본 PDF와 대조하여 문제를 찾아냅니다.
"""

import json
import re
import fitz
from pathlib import Path
from typing import List, Dict, Tuple

class DataValidator:
    def __init__(self):
        self.issues = []
        self.pdf_cache = {}
    
    def load_pdf(self, pdf_path: str) -> str:
        """PDF를 로드하고 텍스트 추출"""
        if pdf_path not in self.pdf_cache:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text("text") + "\n"
            doc.close()
            self.pdf_cache[pdf_path] = text
        return self.pdf_cache[pdf_path]
    
    def validate_chunk(self, chunk: Dict, pdf_text: str) -> List[str]:
        """개별 청크 검증"""
        issues = []
        text = chunk.get('text', '')
        title = chunk.get('title', '')
        article_id = chunk.get('article_id', '')
        
        # 1. 기본 검증
        if len(text.strip()) < 20:
            issues.append(f"너무 짧음 ({len(text.strip())}자)")
        if len(text) > 1200:
            issues.append(f"너무 김 ({len(text)}자)")
        if not text.strip():
            issues.append("빈 텍스트")
        
        # 2. 제어 문자 검증
        if re.search(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', text):
            issues.append("제어 문자 포함")
        if re.search(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', title):
            issues.append("제목에 제어 문자 포함")
        
        # 3. 텍스트 품질 검증
        if re.search(r'[가-힣]\n+[가-힣]', text):
            issues.append("한글 단어 중간 개행")
        if re.search(r'\d+[\^&\*]', text):
            issues.append("이상한 특수문자")
        if '상속민법권' in text:
            issues.append("'상속민법권' 오류")
        if re.search(r'및[가-힣]', text):
            issues.append("'및' 뒤 공백 없음")
        if re.search(r'[가-힣\d]\n+민법\s+\d', text):
            issues.append("PDF 헤더 '민법' 단어 문제")
        # "분의 1" 다음 숫자 붙음 체크
        # 단, "100분의 10", "100분의 100" 같은 정상 패턴은 제외
        if re.search(r'\d분의\s*1\d+', text):
            # "100분의 10" 또는 "100분의 100" 패턴이 아닌 경우만 문제로 표시
            problematic = re.findall(r'\d+분의\s*1\d+', text)
            # "100분의 10", "100분의 100" 제외 (공백 포함/미포함 모두)
            filtered = []
            for p in problematic:
                # "100분의 10", "100분의 100" 패턴인지 확인
                if not (re.search(r'100\s*분의\s*10', p) or re.search(r'100\s*분의\s*100', p) or 
                        re.search(r'100분의\s*10', p) or re.search(r'100분의\s*100', p)):
                    filtered.append(p)
            if filtered:
                issues.append("'분의 1' 다음 숫자 붙음")
        if re.search(r'100분의\s*1\s*\n+\s*0', text):
            issues.append("'100분의 10/100' 잘못 분리")
        if re.search(r'100분의\s*201\)', text):
            issues.append("'100분의 201)' 패턴")
        if re.search(r'__PROTECTED|__TAG|__DATE', text):
            issues.append("보호 마커 남아있음")
        
        # 4. 원본 PDF와 대조 (조문이 있는 경우)
        # 주의: 조문이 분할되어 있으면 키워드 일치도가 낮을 수 있으므로
        # 이 검사는 매우 낮은 경우(5% 미만)만 문제로 표시
        # 또한 짧은 조문(100자 미만)이나 "시행일", "부칙" 같은 것은 제외
        if (article_id and pdf_text and not chunk.get('sub_chunk') and 
            len(text) >= 100 and '시행일' not in title and '부칙' not in title):  # 분할되지 않은 조문만, 100자 이상, 시행일/부칙 제외
            # 조문 번호 추출 (예: "제16조" -> "16")
            match = re.search(r'제(\d+)조', article_id)
            if match:
                article_num = match.group(1)
                # 원본에서 해당 조문 찾기
                pattern = rf'제{article_num}조\([^\)]*\)'
                if re.search(pattern, pdf_text):
                    # 원본 조문의 핵심 키워드가 처리된 텍스트에 있는지 확인
                    article_match = re.search(pattern, pdf_text)
                    if article_match:
                        start = article_match.start()
                        # 다음 조문까지 찾기
                        next_match = re.search(rf'제{int(article_num)+1}조', pdf_text[start:])
                        if next_match:
                            end = start + next_match.start()
                        else:
                            end = start + 5000
                        
                        original_article = pdf_text[start:end]
                        # 핵심 키워드 추출 (한글 단어 3개 이상)
                        keywords = set(re.findall(r'[가-힣]{3,}', original_article[:500]))
                        text_keywords = set(re.findall(r'[가-힣]{3,}', text[:500]))
                        
                        # 키워드 겹침이 매우 적으면 문제 (5% 미만만 문제로 표시)
                        if len(keywords) > 0:
                            overlap = len(keywords & text_keywords) / len(keywords)
                            if overlap < 0.05:  # 5% 미만이면 문제
                                issues.append(f"원본과 키워드 일치도 매우 낮음 ({overlap*100:.1f}%)")
        
        # 5. JSON 형식 검증
        try:
            json.dumps(chunk, ensure_ascii=False)
        except:
            issues.append("JSON 직렬화 실패")
        
        return issues
    
    def validate_file(self, jsonl_path: str, pdf_path: str = None) -> Dict:
        """JSONL 파일 전체 검증"""
        results = {
            'file': jsonl_path,
            'total_chunks': 0,
            'issues': [],
            'issue_count': 0
        }
        
        pdf_text = None
        if pdf_path and Path(pdf_path).exists():
            pdf_text = self.load_pdf(pdf_path)
        
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    chunk = json.loads(line)
                    results['total_chunks'] += 1
                    
                    chunk_issues = self.validate_chunk(chunk, pdf_text)
                    if chunk_issues:
                        results['issues'].append({
                            'line': line_num,
                            'id': chunk.get('id', 'unknown'),
                            'issues': chunk_issues
                        })
                        results['issue_count'] += len(chunk_issues)
                except json.JSONDecodeError as e:
                    results['issues'].append({
                        'line': line_num,
                        'id': 'unknown',
                        'issues': [f"JSON 파싱 오류: {e}"]
                    })
                    results['issue_count'] += 1
                except Exception as e:
                    results['issues'].append({
                        'line': line_num,
                        'id': 'unknown',
                        'issues': [f"오류: {e}"]
                    })
                    results['issue_count'] += 1
        
        return results
    
    def validate_all(self, processed_dir: str = "processed", pdf_dir: str = ".") -> List[Dict]:
        """모든 처리된 파일 검증"""
        file_mapping = {
            "1_minbeob_sangsok_chunks.jsonl": "1. 민법 상속편.pdf",
            "2_segeumsangsik_I_simple.jsonl": "2. 국세청-상속·증여 세금상식1.pdf",
            "3_segeumsangsik_II_simple.jsonl": "3. 국세청-상속·증여 세금상식2.pdf",
            "4_ansimsangsok_web_simple.jsonl": "4. 사망자 및 피후견인 등 재산조회 통합처리 신청(안심상속)웹스크래핑.pdf",
            "5_jaesanjohoe_rule_chunks.jsonl": "5. 사망자 및 피후견인 등 재산조회 통합처리에 관한 기준(행정안전).pdf",
            "6_sangsokse_beob_chunks.jsonl": "6. 상속세 및 증여세법.pdf",
        }
        
        all_results = []
        for jsonl_file, pdf_file in file_mapping.items():
            jsonl_path = Path(processed_dir) / jsonl_file
            pdf_path = Path(pdf_dir) / pdf_file
            
            if jsonl_path.exists():
                result = self.validate_file(str(jsonl_path), str(pdf_path) if pdf_path.exists() else None)
                all_results.append(result)
            else:
                all_results.append({
                    'file': jsonl_file,
                    'error': '파일 없음'
                })
        
        return all_results

def main():
    validator = DataValidator()
    results = validator.validate_all()
    
    print("="*70)
    print("전체 데이터 검증 결과")
    print("="*70)
    
    total_chunks = 0
    total_issues = 0
    
    for result in results:
        if 'error' in result:
            print(f"\n{result['file']}: {result['error']}")
            continue
        
        print(f"\n{result['file']}:")
        print(f"  총 청크: {result['total_chunks']}개")
        print(f"  발견된 문제: {result['issue_count']}개")
        
        if result['issues']:
            print(f"  문제 상세:")
            for issue in result['issues'][:10]:  # 최대 10개만 표시
                print(f"    라인 {issue['line']} (ID: {issue['id']}):")
                for i in issue['issues']:
                    print(f"      - {i}")
            if len(result['issues']) > 10:
                print(f"    ... 외 {len(result['issues'])-10}개 더")
        
        total_chunks += result['total_chunks']
        total_issues += result['issue_count']
    
    print("\n" + "="*70)
    print(f"전체 요약: {total_chunks}개 청크 중 {total_issues}개 문제 발견")
    print("="*70)
    
    if total_issues == 0:
        print("\n✅ 모든 검증 통과!")
        return 0
    else:
        print(f"\n⚠️ {total_issues}개 문제 발견 - 수정 필요")
        return 1

if __name__ == "__main__":
    exit(main())

