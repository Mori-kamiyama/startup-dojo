import xml.etree.ElementTree as ET
import json
import re

def parse_law_xml(xml_file_path, output_json_path):
    """
    e-Govの法令XMLを解析し、RAG向けのチャンク（条単位）のJSONリストを作成する。
    """
    
    # XMLの読み込み
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
    except Exception as e:
        print(f"Error loading XML: {e}")
        return

    # XMLの名前空間対応（e-Gov XMLは名前空間を持つ場合があるため、tag名のみで検索するヘルパー）
    def get_tag(element):
        return element.tag.split('}')[-1]

    # 法令名を取得
    law_title_elem = root.find(".//LawTitle")
    law_title = law_title_elem.text if law_title_elem is not None else "不明な法令"
    
    chunks = []

    # MainProvision（本則）の中を走査
    main_provision = root.find(".//MainProvision")
    if main_provision is None:
        print("MainProvisionが見つかりませんでした。")
        return

    # 章（Chapter）ごとのループ
    # ※章がない法令の場合は直接Articleを探すロジックが必要だが、労基法には章があるためこの構造でOK
    current_chapter_name = ""
    
    # XMLの構造をフラットに処理するため、Chapterを探しつつ、その中のArticleを探す
    for chapter in main_provision.findall(".//Chapter"):
        chapter_title_elem = chapter.find("ChapterTitle")
        if chapter_title_elem is not None:
            current_chapter_name = chapter_title_elem.text
        
        # 条（Article）ごとのループ
        for article in chapter.findall("Article"):
            article_data = {
                "law_name": law_title,
                "chapter": current_chapter_name,
                "article_id": "",
                "caption": "",
                "text": "",      # 人間が読む用の整形済みテキスト
                "combined_text": "" # ベクトル化（検索）用の統合テキスト
            }

            # 条名（例：第一条）
            article_title = article.find("ArticleTitle")
            if article_title is not None:
                article_data["article_id"] = article_title.text

            # 条見出し（例：労働条件の原則）
            article_caption = article.find("ArticleCaption")
            if article_caption is not None:
                article_data["caption"] = article_caption.text

            # --- 本文の構築ロジック ---
            text_parts = []
            
            # 項（Paragraph）の処理
            for paragraph in article.findall("Paragraph"):
                para_num_elem = paragraph.find("ParagraphNum")
                para_num = para_num_elem.text if para_num_elem is not None else ""
                
                # 項番号の整形（1項は番号がない場合が多いので処理）
                display_para_num = f"【第{para_num}項】" if para_num and para_num != "1" else ""
                
                para_sentences = []
                for sentence in paragraph.findall(".//Sentence"):
                    if sentence.text:
                        para_sentences.append(sentence.text)
                
                full_para_text = "".join(para_sentences)
                text_parts.append(f"{display_para_num} {full_para_text}")

                # 号（Item）の処理（項の中にぶら下がる場合）
                for item in paragraph.findall("Item"):
                    item_title = item.find("ItemTitle")
                    item_num = item_title.text if item_title is not None else "・"
                    
                    item_sentences = []
                    for i_sent in item.findall(".//Sentence"):
                        if i_sent.text:
                            item_sentences.append(i_sent.text)
                    
                    text_parts.append(f"  {item_num} {''.join(item_sentences)}")

            # テキストの結合
            article_data["text"] = "\n".join(text_parts).strip()
            
            # RAG検索用テキストの作成
            # 検索時は「第○条」や「見出し」もヒットしてほしいので、全て結合する
            article_data["combined_text"] = f"{law_title} {current_chapter_name} {article_data['article_id']} {article_data['caption']}\n{article_data['text']}"
            
            chunks.append(article_data)

    # JSONとして保存
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print(f"処理完了: {len(chunks)} 件の条文データを {output_json_path} に保存しました。")
    
    # 確認のため最初の1件を表示
    if chunks:
        print("\n--- サンプルデータ (最初の1件) ---")
        print(json.dumps(chunks[0], ensure_ascii=False, indent=2))

# --- 実行部分 ---
# アップロードされたファイル名を指定してください
input_files = [
    ("322AC0000000049_20250601_504AC0000000068.xml", "labor_standards_act_chunks.json"),
    ("351AC0000000057_20250601_504AC0000000068.xml", "specific_commercial_transaction_act_chunks.json"),
    ("417AC0000000086_20251001_505AC0000000053.xml", "companies_act_chunks.json"),
]

if __name__ == "__main__":
    for xml_file, json_file in input_files:
        parse_law_xml(xml_file, json_file)