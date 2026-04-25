-- Seed categories

INSERT INTO categories (name, slug) VALUES
    ('Вода и напитки', 'voda-i-napitki'),
    ('Хлеб и выпечка', 'khleb-i-vypechka'),
    ('Молочная продукция и яйцо', 'molochnaya-produktsiya-i-yaytso'),
    ('Сладости', 'sladosti'),
    ('Бакалея', 'bakaleya'),
    ('Снеки', 'sneki'),
    ('Еда', 'eda'),
    ('Канцелярия', 'kancelyariya'),
    ('Бытовые мелочи', 'bytovye-melochi'),
    ('Ozon', 'ozon'),
    ('Яндекс Маркет', 'yandex-market')
ON CONFLICT (slug) DO UPDATE
SET name = EXCLUDED.name;


-- Seed products from current MVP

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Вода 0.5 л', 'Питьевая вода в удобной бутылке.', 35.00, 'https://placehold.co/600x400/png?text=Voda+0.5L', c.id, 'internal', TRUE
FROM categories c
WHERE c.slug = 'voda-i-napitki'
  AND NOT EXISTS (
    SELECT 1 FROM products p
    WHERE p.name = 'Вода 0.5 л' AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Чипсы', 'Солёные картофельные чипсы.', 89.00, 'https://placehold.co/600x400/png?text=Chipsy', c.id, 'internal', TRUE
FROM categories c
WHERE c.slug = 'sneki'
  AND NOT EXISTS (
    SELECT 1 FROM products p
    WHERE p.name = 'Чипсы' AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Шоколадный батончик', 'Быстрый перекус к учёбе.', 55.00, 'https://placehold.co/600x400/png?text=Shokolad', c.id, 'internal', TRUE
FROM categories c
WHERE c.slug = 'sneki'
  AND NOT EXISTS (
    SELECT 1 FROM products p
    WHERE p.name = 'Шоколадный батончик' AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Лапша быстрого приготовления', 'Готовится за несколько минут.', 79.00, 'https://placehold.co/600x400/png?text=Lapsha', c.id, 'internal', TRUE
FROM categories c
WHERE c.slug = 'eda'
  AND NOT EXISTS (
    SELECT 1 FROM products p
    WHERE p.name = 'Лапша быстрого приготовления' AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Тетрадь 48 листов', 'Обычная тетрадь для занятий.', 42.00, 'https://placehold.co/600x400/png?text=Tetrad', c.id, 'internal', TRUE
FROM categories c
WHERE c.slug = 'kancelyariya'
  AND NOT EXISTS (
    SELECT 1 FROM products p
    WHERE p.name = 'Тетрадь 48 листов' AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Ручка шариковая', 'Синяя шариковая ручка.', 25.00, 'https://placehold.co/600x400/png?text=Ruchka', c.id, 'internal', TRUE
FROM categories c
WHERE c.slug = 'kancelyariya'
  AND NOT EXISTS (
    SELECT 1 FROM products p
    WHERE p.name = 'Ручка шариковая' AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Салфетки влажные', 'Удобно взять с собой.', 60.00, 'https://placehold.co/600x400/png?text=Salfetki', c.id, 'ozon', TRUE
FROM categories c
WHERE c.slug = 'bytovye-melochi'
  AND NOT EXISTS (
    SELECT 1 FROM products p
    WHERE p.name = 'Салфетки влажные' AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Портативный аккумулятор', 'Power bank для телефона.', 1290.00, 'https://placehold.co/600x400/png?text=Power+Bank', c.id, 'yandex_market', TRUE
FROM categories c
WHERE c.slug = 'bytovye-melochi'
  AND NOT EXISTS (
    SELECT 1 FROM products p
    WHERE p.name = 'Портативный аккумулятор' AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Зубная паста', 'Компактный вариант для общежития.', 149.00, 'https://placehold.co/600x400/png?text=Zubnaya+Pasta', c.id, 'ozon', TRUE
FROM categories c
WHERE c.slug = 'bytovye-melochi'
  AND NOT EXISTS (
    SELECT 1 FROM products p
    WHERE p.name = 'Зубная паста' AND p.category_id = c.id
  );


-- Seed products from previous seed

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Напиток энергетический Aziano Energy Power тонизирующий газированный 350мл',
       'Газированный энергетический напиток 350 мл.',
       97.99,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'voda-i-napitki'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Напиток энергетический Aziano Energy Power тонизирующий газированный 350мл'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Напиток энергетический Adrenaline Extra 0.449л',
       'Газированный энергетик 449 мл.',
       139.99,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'voda-i-napitki'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Напиток энергетический Adrenaline Extra 0.449л'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Напиток Evervess Индиан Тоник газированный 1л',
       'Газированный тоник 1 л.',
       189.90,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'voda-i-napitki'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Напиток Evervess Индиан Тоник газированный 1л'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Напиток Святой источник Вода+сок манго-маракуйя газированный 1л',
       'Освежающий напиток с соком манго и маракуйи, 1 л.',
       93.99,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'voda-i-napitki'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Напиток Святой источник Вода+сок манго-маракуйя газированный 1л'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Напиток Lifeline арбуз-яблоко негазированный 0.5л',
       'Негазированный напиток со вкусом арбуза и яблока, 500 мл.',
       99.99,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'voda-i-napitki'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Напиток Lifeline арбуз-яблоко негазированный 0.5л'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Лаваш Рижский хлеб из пшеничной муки 200г',
       'Лаваш из пшеничной муки, 200 г.',
       93.99,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'khleb-i-vypechka'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Лаваш Рижский хлеб из пшеничной муки 200г'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Лаваш Рижский Хлеб мини из пшеничной муки 200г',
       'Мини-лаваш из пшеничной муки, 200 г.',
       82.99,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'khleb-i-vypechka'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Лаваш Рижский Хлеб мини из пшеничной муки 200г'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Соломка Жуковский Хлеб сдобная с маком 200г',
       'Сдобная соломка с маком, 200 г.',
       64.99,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'khleb-i-vypechka'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Соломка Жуковский Хлеб сдобная с маком 200г'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Батон Черемушки Полюшко нарезка 300г',
       'Нарезной батон, 300 г.',
       79.99,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'khleb-i-vypechka'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Батон Черемушки Полюшко нарезка 300г'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Хлеб Маркет Collection Ржевский цельнозерновой 450г',
       'Цельнозерновой хлеб, 450 г.',
       99.99,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'khleb-i-vypechka'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Хлеб Маркет Collection Ржевский цельнозерновой 450г'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Молоко Parmalat Comfort ультрапастеризованное безлактозное 1.8% БЗМЖ 1л',
       'Безлактозное ультрапастеризованное молоко 1 л.',
       149.99,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'molochnaya-produktsiya-i-yaytso'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Молоко Parmalat Comfort ультрапастеризованное безлактозное 1.8% БЗМЖ 1л'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Кефир Станция Молочная 1% БЗМЖ 930г',
       'Кефир 1%, 930 г.',
       96.99,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'molochnaya-produktsiya-i-yaytso'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Кефир Станция Молочная 1% БЗМЖ 930г'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Творог Станция Молочная 5% БЗМЖ 180г',
       'Творог 5%, 180 г.',
       74.99,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'molochnaya-produktsiya-i-yaytso'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Творог Станция Молочная 5% БЗМЖ 180г'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Сметана Станция Молочная 15% БЗМЖ 300г',
       'Сметана 15%, 300 г.',
       84.99,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'molochnaya-produktsiya-i-yaytso'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Сметана Станция Молочная 15% БЗМЖ 300г'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Йогурт питьевой Epica киви и виноград 2.5% 260мл',
       'Питьевой йогурт с киви и виноградом, 260 мл.',
       69.99,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'molochnaya-produktsiya-i-yaytso'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Йогурт питьевой Epica киви и виноград 2.5% 260мл'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Мармелад Мармеладная Сказка с апельсином и красным перцем желейный 300г',
       'Желейный мармелад, 300 г.',
       249.99,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'sladosti'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Мармелад Мармеладная Сказка с апельсином и красным перцем желейный 300г'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Зефир Живые конфеты лимон-малина-ваниль на фруктозе 240г',
       'Зефир на фруктозе, 240 г.',
       249.99,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'sladosti'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Зефир Живые конфеты лимон-малина-ваниль на фруктозе 240г'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Пастила Шармэль йогурт 221г',
       'Пастила со вкусом йогурта, 221 г.',
       218.99,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'sladosti'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Пастила Шармэль йогурт 221г'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Конфеты Twix Minis с карамелью в молочном шоколаде 184г',
       'Мини-конфеты Twix с карамелью, 184 г.',
       299.99,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'sladosti'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Конфеты Twix Minis с карамелью в молочном шоколаде 184г'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Батончик вафельный Kinder Bueno 3х43г',
       'Вафельный батончик с кремовой начинкой, 3 шт.',
       279.99,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'sladosti'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Батончик вафельный Kinder Bueno 3х43г'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Макароны Pasteroni Фарфалле №170 400г',
       'Макароны фарфалле, 400 г.',
       129.00,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'bakaleya'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Макароны Pasteroni Фарфалле №170 400г'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Макароны Makfa Спирали 450г',
       'Макароны спирали, 450 г.',
       72.00,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'bakaleya'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Макароны Makfa Спирали 450г'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Кофе Carte Noire Original жареный в зёрнах 800г',
       'Кофе в зёрнах, 800 г.',
       2599.00,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'bakaleya'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Кофе Carte Noire Original жареный в зёрнах 800г'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Кофе молотый Lavazza Qualita Oro 250г',
       'Молотый кофе, 250 г.',
       1199.00,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'bakaleya'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Кофе молотый Lavazza Qualita Oro 250г'
        AND p.category_id = c.id
  );

INSERT INTO products (name, description, price, image_url, category_id, source_type, is_available)
SELECT 'Соль 4Life Морская йодированная мелкая 1кг',
       'Морская йодированная соль, 1 кг.',
       145.99,
       NULL,
       c.id,
       'internal',
       TRUE
FROM categories c
WHERE c.slug = 'bakaleya'
  AND NOT EXISTS (
      SELECT 1 FROM products p
      WHERE p.name = 'Соль 4Life Морская йодированная мелкая 1кг'
        AND p.category_id = c.id
  );