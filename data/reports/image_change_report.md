# 레시피 이미지 재생성 변경 리포트

생성일: 2026-03-03

## 변경 개요

### 이전 시스템 (Old)
- 프롬프트: 레시피 영문명만 전달 (예: `"food photo of Vietnamese Beef Pho"`)
- 카테고리 스타일: 없음 (모든 요리가 동일 구도)
- 재료 반영: 없음
- 결과: 요리와 무관한 이미지 다수 (스무디→비빔밥, 전골→접시 등)

### 새 시스템 (New)
- 프롬프트: 영문명 + 핵심 재료(회사 제품 제외) + 카테고리별 프레젠테이션 스타일
- 3가지 스타일:
  - **Bowl** (국물/면): `Served in a deep ceramic bowl, seen from 45-degree angle`
  - **Plate** (구이/볶음/밥/샐러드/스낵/디저트): `Plated on a round ceramic dish, seen from above`
  - **Glass** (음료): `In a tall clear glass, seen from eye level`
- 공통 스타일: `Light wooden table, warm natural side lighting, vibrant colors, sharp focus`
- 재료 필터: 다미푸드 제품(코인육수, 시즈닝 등) + 기본 조미료(소금, 설탕 등) 자동 제외

## 수량 변화

| 항목 | 이전 | 이후 |
|------|------|------|
| 전체 레시피 | 81 | 81 |
| 이미지 있음 | 55 | 81 (목표) |
| 이미지 없음 | 26 | 0 (목표) |
| Orphan 이미지 | 17 | 0 |
| 캐시 항목 | 72 | 81 (목표) |

## 스타일별 분포

| 스타일 | 레시피 수 | 카테고리 |
|--------|----------|----------|
| 🥣 Bowl | 33 | 국물, 면 |
| 🍽️ Plate | 43 | 구이, 볶음, 밥, 샐러드, 스낵, 디저트 |
| 🥤 Glass | 5 | 음료 |

## 🥣 BOWL 스타일 (33개)

| # | 레시피 | 카테고리 | 핵심 재료 | 이전 이미지 |
|---|--------|----------|-----------|------------|
| 1 | 감자탕 시즈닝 반깐 (타피오카 면 국수) | 국물 | Pork ribs, Shrimp, Garlic, Fried onions, Green oni... | 있음 |
| 2 | 후에식 매운 소고기 국수 | 면 | beef brisket, pork trotters or pork tenderloin, le... | 있음 |
| 3 | 소고기 볶음 쌀국수 (국물 버전) | 면 | onion, tomato, green onion, bean sprouts, garlic | 있음 |
| 4 | 생선 국수 (새콤한 버전) | 면 | white fish, tomatoes, pineapple, dill, turmeric po... | 있음 |
| 5 | 분짜 쌈장허브 디핑 | 면 | ground pork, lettuce, cilantro, mint, perilla, pic... | 있음 |
| 6 | 채식 분리우 | 면 | tofu, tomatoes, tamarind paste, fermented tofu, gr... | 있음 |
| 7 | 하노이식 맑은 국수 | 면 | chicken breast, cha siu, radish, dried shiitake mu... | 있음 |
| 8 | K-로제 볶음 분 | 면 | chicken breast, onion, carrot, bok choy, garlic | 있음 |
| 9 | 생선 맑은탕 | 국물 | white fish, tomato, dill, green onions, garlic | 있음 |
| 10 | 새콤한 생선탕 | 국물 | white fish, pineapple, tomato, bean sprouts, okra | 있음 |
| 11 | 모둠 새콤탕 | 국물 | shrimp, squid, white fish, pineapple, tomato | 있음 |
| 12 | 새콤한 새우탕 | 국물 | shrimp, pineapple, tomato, bean sprouts, okra | **없음** |
| 13 | 버섯 맑은탕 | 국물 | large king oyster mushrooms, shiitake mushrooms, o... | 있음 |
| 14 | 공심채 맑은국 | 국물 | Garlic, Tomato | 있음 |
| 15 | 감자탕 시즈닝 까인 쓰엉 (뼈 육수 국) | 국물 | Pork back bones, Daikon radish, Green onions, Cila... | 있음 |
| 16 | 전복죽 시즈닝 짜오 바오 응우 (베트남식 전복죽) | 국물 | ginger, green onions, little cilantro, fried onion... | 있음 |
| 17 | 전복죽 시즈닝 짜오 가 (닭죽 프리미엄) | 국물 | chicken leg, green onions, cilantro, fried onions,... | 있음 |
| 18 | 전복죽 시즈닝 짜오 하이 산 (해산물 죽) | 국물 | shrimp, squid, scallops, ginger, garlic | **없음** |
| 19 | 감자탕 시즈닝 짜오 쓰언 (돼지갈비 죽) | 국물 | pork ribs, fried onions, green onions, little cori... | 있음 |
| 20 | 김부각 칩 쌀국수 토핑 | 면 | Basic accompaniments  bean sprouts, lime, chili, a... | **없음** |
| 21 | 소고기 스튜 후띠우 | 면 | Beef shank or short ribs, carrot, lemongrass, star... | **없음** |
| 22 | 소고기 전골 | 국물 | napa cabbage, corn, oyster mushrooms, enoki mushro... | 있음 |
| 23 | 채식 전골 | 국물 | tofu, shiitake mushrooms, oyster mushrooms, enoki ... | 있음 |
| 24 | 새콤매콤 전골 | 국물 | shrimp, squid, beef for shabu-shabu, napa cabbage,... | 있음 |
| 25 | 버섯 전골 | 국물 | large king oyster mushrooms, shiitake mushrooms, o... | 있음 |
| 26 | 감자탕 시즈닝 러우 쓰엉 (뼈 전골) | 국물 | Pork bones, Potato, Corn, Napa cabbage, Enoki mush... | 있음 |
| 27 | 꽝남식 넓은 면 | 면 | Shrimp, Chicken thigh meat, Turmeric powder, Onion... | **없음** |
| 28 | K-로제 해산물 볶음면 | 면 | shrimp, broccoli, onion, garlic | **없음** |
| 29 | 소고기 쌀국수 | 면 | beef shank or brisket, bean sprouts, onion, green ... | 있음 |
| 30 | 채식 쌀국수 | 면 | firm tofu, shiitake mushrooms, broccoli, carrot, b... | 있음 |
| 31 | 닭고기 쌀국수 | 면 | chicken breast or thigh, onion, ginger, cinnamon s... | **없음** |
| 32 | K-로제 볶음 쌀국수 | 면 | cabbage, bean sprouts, scallions, garlic | 있음 |
| 33 | 전복죽 시즈닝 숩 하이 산 (해산물 수프) | 국물 | Shrimp, Squid, Crab stick, Corn kernels, Garlic | **없음** |

## 🍽️ PLATE 스타일 (43개)

| # | 레시피 | 카테고리 | 핵심 재료 | 이전 이미지 |
|---|--------|----------|-----------|------------|
| 1 | 청양마요 반미 샌드위치 | 밥 | baguettes, pork shoulder, carrot, radish, cucumber | 있음 |
| 2 | 불고기 시즈닝 반미 | 구이 | baguette breads, carrot, radish, cilantro, green c... | 있음 |
| 3 | 반쎄오 청양마요 디핑 | 볶음 | turmeric powder, coconut milk, medium-sized shrimp... | 있음 |
| 4 | 불고기 시즈닝 보 룩 락 | 볶음 | beef tenderloin or sirloin, onion, garlic, butter,... | 있음 |
| 5 | 로롯 잎 소고기 구이 쌈장허브 곁들임 | 구이 | ground beef, wild betel leaf, lemongrass, garlic, ... | **없음** |
| 6 | 불고기코코넛 소고기 구이 | 구이 | garlic, lemongrass, lettuce, cilantro, mint, peril... | 있음 |
| 7 | 망고고추장 닭날개 튀김 | 볶음 | chicken wings, starch, garlic powder, toasted sesa... | 있음 |
| 8 | 망고고추장 닭날개 구이 | 구이 | chicken wings, garlic, toasted sesame seeds | 있음 |
| 9 | 닭갈비 시즈닝 치즈볼 | 스낵 | Mozzarella cheese, Breadcrumbs | 있음 |
| 10 | 김부각 초콜릿 크런치 바 | 스낵 | Dark chocolate, Roasted peanuts, Dried mango, Coco... | 있음 |
| 11 | 감자탕 시즈닝 껌찌엔 (볶음밥) | 밥 | shrimp, carrot, green peas, green onion, garlic | 있음 |
| 12 | 닭갈비 시즈닝 껌가 (호이안식 닭고기 밥) | 밥 | chicken thighs, garlic, turmeric powder, Vietnames... | **없음** |
| 13 | 쩜떰 청양마요 곁들임 | 밥 | Pork ribs, cucumber, tomato, Pickled radish | **없음** |
| 14 | 불고기 시즈닝 쩜떰 | 밥 | pork ribs, garlic, lemongrass | **없음** |
| 15 | 망고고추장 바삭 닭다리 튀김 | 볶음 | chicken drumsticks, garlic, ginger, lime, little c... | 있음 |
| 16 | 불고기코코넛 꿀 닭구이 | 구이 | chicken  or chicken thighs, honey, garlic, ginger,... | 있음 |
| 17 | 닭갈비 시즈닝 가느엉 (닭구이) | 구이 | chicken thighs or wings, lemongrass, garlic, honey... | 있음 |
| 18 | 망고고추장 베트남 프라이드치킨 | 볶음 | chicken thighs or drumsticks, garlic, lime wedges,... | **없음** |
| 19 | 닭갈비 시즈닝 가 싸오 사 엇 (레몬그라스 닭볶음) | 볶음 | chicken thigh, garlic, onion | 있음 |
| 20 | K-로제 닭볶음 | 볶음 | chicken thigh, onion, lemongrass, garlic | 있음 |
| 21 | 김부각 칩 맥주 안주 플래터 | 스낵 | lime wedges | **없음** |
| 22 | 김부각 칩 쩜떰 토핑 | 밥 | (dish name only) | **없음** |
| 23 | 김부각 칩 베트남 샐러드 토핑 | 샐러드 | shredded green papaya or green mango, herbs  cilan... | 있음 |
| 24 | 튀긴 스프링롤 청양마요 딥 | 볶음 | shrimp, glass noodles, ground pork, dried wood ear... | **없음** |
| 25 | 구운고기 월남쌈 쌈장허브 디핑 | 샐러드 | pork neck, lettuce, cilantro, mint, perilla | 있음 |
| 26 | 새우 월남쌈 매실 디핑 | 샐러드 | medium-sized shrimp, lettuce, cilantro, mint, chiv... | 있음 |
| 27 | 닭갈비 시즈닝 고이 가 (닭고기 샐러드) | 샐러드 | chicken breast, cabbage, carrot, Vietnamese corian... | **없음** |
| 28 | 해산물 샐러드 매실 드레싱 | 샐러드 | shrimp, squid, celery, carrot, cilantro | 있음 |
| 29 | 구운 해산물 플래터 매실 디핑 | 구이 | large shrimp, squid, scallops, garlic, green onion... | **없음** |
| 30 | 망고 고추장 아이스바 | 디저트 | ripe mangoes, plain yogurt, sweetened condensed mi... | **없음** |
| 31 | 미숫가루 바나나 케이크 (bánh chuối) | 디저트 | ripe bananas, coconut milk, little butter | 있음 |
| 32 | 미숫가루 코코넛 체 (chè) | 디저트 | Coconut milk, Tapioca pearls, Cooked red beans | 있음 |
| 33 | 네무엉 쌈장허브 디핑 | 구이 | ground pork, pork fat, garlic, baking powder, lett... | **없음** |
| 34 | 미숫가루 코코넛 빙수 | 디저트 | cooked red beans, coconut milk, condensed milk, ta... | 있음 |
| 35 | 닭갈비 시즈닝 퍼가 싸오 (닭고기 볶음 쌀국수) | 볶음 | onion, Bok choy, Bean sprouts, garlic, Lime wedges | 있음 |
| 36 | 불고기 시즈닝 팝콘 | 스낵 | popcorn kernels, butter | **없음** |
| 37 | 불고기코코넛 돼지갈비 구이 | 구이 | pork ribs, garlic, shallots, honey, lime | 있음 |
| 38 | 불고기코코넛 숯불고기 | 구이 | garlic, shallots, lettuce, cilantro, mint, pickled... | 있음 |
| 39 | 불고기 시즈닝 숯불구이 (분팃느엉용) | 구이 | Lettuce, perilla , cilantro  each a, Bean sprouts,... | 있음 |
| 40 | 찐 새우 매실 디핑 | 구이 | large shrimp, lemongrass, lime | 있음 |
| 41 | 망고 고추장 떡볶이 간식 | 스낵 | Fish cake, Mozzarella cheese | 있음 |
| 42 | 불고기 시즈닝 쏘이 (찹쌀밥 토핑) | 밥 | fried onions, peanuts, shredded pork or pork floss | **없음** |
| 43 | 전복죽 시즈닝 쏘이 (전복 풍미 찹쌀밥) | 밥 | mung beans, fried onions, scallions | **없음** |

## 🥤 GLASS 스타일 (5개)

| # | 레시피 | 카테고리 | 핵심 재료 | 이전 이미지 |
|---|--------|----------|-----------|------------|
| 1 | 미숫가루 베트남 커피 아이스 블렌드 | 음료 | Vietnamese coffee  shots, sweetened condensed milk... | **없음** |
| 2 | 미숫가루 라떼 (연유커피 대체) | 음료 | Milk or coconut milk, Sweetened condensed milk | **없음** |
| 3 | 미숫가루 코코넛 sinh tố | 음료 | Coconut milk, ripe banana, condensed milk | 있음 |
| 4 | 미숫가루 바나나 셰이크 | 음료 | ripe bananas, milk, condensed milk, honey, little ... | 있음 |
| 5 | 매콤 망고 스무디 | 음료 | ripe mango, plain yogurt, sweetened condensed milk... | **없음** |

## 프롬프트 변경 예시

### 미숫가루 코코넛 스무디 (K-Grain Coconut Smoothie)
- **카테고리**: 음료 → **스타일**: glass
- **이전 프롬프트**: `food photo of K-Grain Coconut Smoothie`
- **새 프롬프트**:
```
Professional food photo of K-Grain Coconut Smoothie, with Coconut milk, ripe banana, condensed milk.
In a tall clear glass, seen from eye level.
Light wooden table, warm natural side lighting, vibrant colors, sharp focus.
```

### 소고기 쌀국수 (Vietnamese Beef Pho)
- **카테고리**: 면 → **스타일**: bowl
- **이전 프롬프트**: `food photo of Vietnamese Beef Pho`
- **새 프롬프트**:
```
Professional food photo of Vietnamese Beef Pho, with beef shank or brisket, bean sprouts, onion, green onion, cilantro.
Served in a deep ceramic bowl, seen from 45-degree angle.
Light wooden table, warm natural side lighting, vibrant colors, sharp focus.
```

### 불고기 시즈닝 반미 (Grilled Pork Banh Mi with Bulgogi Seasoning)
- **카테고리**: 구이 → **스타일**: plate
- **이전 프롬프트**: `food photo of Grilled Pork Banh Mi with Bulgogi Seasoning`
- **새 프롬프트**:
```
Professional food photo of Grilled Pork Banh Mi with Bulgogi Seasoning, with baguette breads, carrot, radish, cilantro, green chili.
Plated on a round ceramic dish, seen from above.
Light wooden table, warm natural side lighting, vibrant colors, sharp focus.
```

### 후에식 매운 소고기 국수 (Hue-Style Spicy Beef Noodle Soup)
- **카테고리**: 면 → **스타일**: bowl
- **이전 프롬프트**: `food photo of Hue-Style Spicy Beef Noodle Soup`
- **새 프롬프트**:
```
Professional food photo of Hue-Style Spicy Beef Noodle Soup, with beef brisket, pork trotters or pork tenderloin, lemongrass, shrimp paste, chili powder.
Served in a deep ceramic bowl, seen from 45-degree angle.
Light wooden table, warm natural side lighting, vibrant colors, sharp focus.
```

### 닭갈비 시즈닝 닭구이 (Vietnamese Grilled Chicken with Dakgalbi Seasoning)
- **카테고리**: 구이 → **스타일**: plate
- **이전 프롬프트**: `food photo of Vietnamese Grilled Chicken with Dakgalbi Seasoning`
- **새 프롬프트**:
```
Professional food photo of Vietnamese Grilled Chicken with Dakgalbi Seasoning, with chicken thighs or wings, lemongrass, garlic, honey, lime wedges, cilantro.
Plated on a round ceramic dish, seen from above.
Light wooden table, warm natural side lighting, vibrant colors, sharp focus.
```

## 주요 개선 포인트

1. **음료 레시피 → Glass 스타일**: 이전에는 음료도 접시/그릇 사진으로 생성됨. 이제 유리잔 eye-level로 생성
2. **국물/면 → Bowl 스타일**: 45도 각도 ceramic bowl로 국물 요리 특성 반영
3. **핵심 재료 표시**: 각 요리의 시각적 핵심 재료 3~5개가 프롬프트에 포함
4. **회사 제품 자동 필터**: 코인육수, 시즈닝 등 다미푸드 제품명이 이미지에 노출되지 않음
5. **일관된 스타일**: 모든 이미지가 동일한 배경(나무 테이블), 조명(따뜻한 자연 측광)으로 통일
6. **Orphan 정리**: 존재하지 않는 레시피 ID의 이미지 17개 삭제

---
생성일: 2026-03-03