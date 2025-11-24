"""
Car models expansion dictionary
Maps compact model names to their expanded variants
"""

models_with_dash_eur = ['Honda CR-V',
 'BMW 1 E81-88',
 'BMW 3 E90-93',
 'BMW 5 E60-61',
 'BMW 6 E63-64',
 'Ford C-MAX',
 'Ford B-MAX',
 'Ford S-MAX',
 'Hyundai i-30',
 'Hyundai H-1',
 'Hyundai i-10',
 'Hyundai i-20',
 'Mazda CX-7',
 'Mazda CX-9',
 'Mercedes-Benz C-Class W203',
 'Mercedes-Benz CLK W209',
 'Mercedes-Benz SLK R171',
 'Mercedes-Benz C-Class W204',
 'Mercedes-Benz E-Class W212',
 'Mercedes-Benz CL C216',
 'Mercedes-Benz GLK X204',
 'Mercedes-Benz S-Class W221',
 'Mercedes-Benz E-Class W207',
 'Mercedes-Benz E-Class W210',
 'Mercedes-Benz E-Class W211',
 'Mercedes-Benz CLS C219',
 'Mercedes-Benz GL X164',
 'Mercedes-Benz ML W164',
 'Mercedes-Benz ML W163',
 'Mercedes-Benz Sprinter 901-905',
 'VW LT28-55',
 'Mercedes-Benz Sprinter 906',
 'Mercedes-Benz Vito W638',
 'Mercedes-Benz Viano W639',
 'Mercedes-Benz Vito W639',
 'Citroen C-Crosser',
 'Nissan 10-Trail T31',
 'Nissan 10-Trail T30',
 'Mercedes-Benz Citan',
 'VW Passat B3-B4',
 'Nissan 10-Trail T32',
 'Isuzu D-MAX',
 'SAAB 9-3',
 'Mazda CX-5',
 'Kia e-Soul',
 'Hyundai i-40',
 'Hyundai H-100',
 'Mazda CX-3',
 'BMW 5 F10-18',
 'BMW 6 F06-13',
 'BMW 7 F01-F04',
 'Toyota C-HR',
 'Mazda CX-30',
 'Mercedes-Benz A-Class W168',
 'Mercedes-Benz Vaneo',
 'Mercedes-Benz S-Class W220',
 'Suzuki SX-4 S-Cross',
 'Opel Ampera-е',
 'VW T-Cross',
 'Mazda CX-50',
 'Mercedes-Benz 10-Class',
 'BMW 7 E65-68',
 'Mercedes-Benz CLC',
 'Mercedes-Benz CL C215',
 'Honda HR-V',
 'Honda M-NV']

models_with_dash_gur = ['Audi Q4 E-Tron',
 'Audi e-tron',
 'BMW 1 E81-88',
 'BMW 2 F22-23',
 'BMW 3 E90-93',
 'BMW 3 F30-80',
 'BMW 3 G20-21',
 'BMW 4 F32-36',
 'BMW 4 G22-26',
 'BMW 5 F10-18',
 'BMW 5 G30-38',
 'BMW 6 F06-13',
 'BMW 7 F01-F04',
 'BMW 7 G11-12',
 'BMW 8 G14-16',
 'BMW M3 G80-81',
 'BMW M8 F91-93',
 'BMW X1 F48-49',
 'Citroen C-Elysеe',
 'Ford C-MAX',
 'Ford S-MAX',
 'Honda CR-V',
 'Honda HR-V',
 'Jaguar 1-Pace',
 'Jaguar E-Pace',
 'Jaguar F-Pace',
 'Jaguar F-Type',
 'Mazda CX-60',
 'Mazda CX-90',
 'Mercedes-AMG GT 4-Door Coupe',
 'Mercedes-AMG SL R232',
 'Mercedes-Benz A-Class W169',
 'Mercedes-Benz A-Class W176',
 'Mercedes-Benz A-Class W177',
 'Mercedes-Benz B-Class W242-246',
 'Mercedes-Benz B-Class W245',
 'Mercedes-Benz B-Class W247',
 'Mercedes-Benz C-Class W204',
 'Mercedes-Benz C-Class W205',
 'Mercedes-Benz C-Class W206',
 'Mercedes-Benz CLA',
 'Mercedes-Benz CLS C218',
 'Mercedes-Benz Citan',
 'Mercedes-Benz E-Class W207',
 'Mercedes-Benz E-Class W212',
 'Mercedes-Benz E-Class W213',
 'Mercedes-Benz E-Class W214',
 'Mercedes-Benz EQA',
 'Mercedes-Benz EQB',
 'Mercedes-Benz EQC',
 'Mercedes-Benz EQE',
 'Mercedes-Benz EQS',
 'Mercedes-Benz G-Class W463',
 'Mercedes-Benz GL X166',
 'Mercedes-Benz GLA X156',
 'Mercedes-Benz GLC C253',
 'Mercedes-Benz GLC C254',
 'Mercedes-Benz GLE Coupe C292',
 'Mercedes-Benz GLE W166',
 'Mercedes-Benz GLE W167',
 'Mercedes-Benz GLK X204',
 'Mercedes-Benz GLS X166',
 'Mercedes-Benz GLS X167',
 'Mercedes-Benz ML W166',
 'Mercedes-Benz S-Class W217',
 'Mercedes-Benz S-Class W222',
 'Mercedes-Benz S-Class W223',
 'Mercedes-Benz SL R231',
 'Mercedes-Benz Sprinter 907-910',
 'Mercedes-Benz Vito W447',
 'Peugeot e-2008',
 'Peugeot e-208',
 'Suzuki SX-4',
 'VW T-Roc',
 'VW e-Bora',
 'VW e-Golf 7',
 'VW e-Lavida']

models_expanded_eur = {
    'BMW 1 E81-88': [
        'E81',  # 3-door hatchback (2007-2012)
        'E82',  # Coupe (2007-2013)
        'E87',  # 5-door hatchback (2004-2011)
        'E88'   # Convertible (2007-2013)
    ],
    'BMW 3 E90-93': [
        'E90',  # Sedan/Saloon (2005-2011)
        'E91',  # Estate/Touring (2005-2012)
        'E92',  # Coupe (2006-2013)
        'E93'   # Convertible (2007-2013)
    ],
    'BMW 5 E60-61': [
        'E60',  # Sedan/Saloon (2003-2010)
        'E61'   # Estate/Touring (2004-2010)
    ],
    'BMW 6 E63-64': [
        'E63',  # Coupe (2003-2010)
        'E64'   # Convertible (2004-2010)
    ],
    'Mercedes-Benz Sprinter 901-905': [
        '901',  # First models (1995-1997)
        '902',  # Light-duty models (1998-2006)
        '903',  # Medium-duty models (1998-2006)
        '904',  # Heavy-duty models (1998-2006)
        '905'   # Specialty configurations (1998-2006)
    ],
    'VW LT28-55': [
        'LT28',  # 2.8 Tonnes GVW (1975-1996)
        'LT31',  # 3.1 Tonnes GVW (1975-1996)
        'LT35',  # 3.5 Tonnes GVW (1976-1996)
        'LT46',  # 4.6 Tonnes GVW (1985-1996)
        'LT55'   # 5.6 Tonnes GVW (1985-1996)
    ],
    'VW Passat B3-B4': [
        'B3',  # Third generation (1988-1993)
        'B4'   # Facelift of B3 (1993-1997)
    ],
    'SAAB 9-3': [
        '9-3 YS3D',  # First generation (1998-2003)
        '9-3 YS3F'   # Second generation (2003-2012)
    ],
    'BMW 5 F10-18': [
        'F07',  # Gran Turismo fastback (2009-2017)
        'F10',  # Sedan/Saloon (2010-2017)
        'F11',  # Estate/Touring (2010-2017)
        'F18'   # Long-wheelbase sedan (2010-2017)
    ],
    'BMW 6 F06-13': [
        'F06',  # Gran Coupe 4-door (2012-2018)
        'F12',  # Convertible 2-door (2011-2018)
        'F13'   # Coupe 2-door (2011-2017)
    ],
    'BMW 7 F01-F04': [
        'F01',  # Standard wheelbase sedan (2008-2015)
        'F02',  # Long wheelbase sedan (2008-2015)
        'F03',  # High Security armored (2008-2015)
        'F04'   # ActiveHybrid model (2008-2015)
    ],
    'BMW 7 E65-68': [
        'E65',  # Standard wheelbase sedan (2001-2008)
        'E66',  # Long wheelbase "Li" models (2002-2008)
        'E67',  # High Security armored (2003-2008)
        'E68'   # Hydrogen 7 model (2006-2008)
    ]
}

models_expanded_gur = {
    'BMW 1 E81-88': [
        'E81',  # 3-door hatchback (2007-2012)
        'E82',  # Coupe (2007-2013)
        'E87',  # 5-door hatchback (2004-2011)
        'E88'   # Convertible (2007-2013)
    ],
    'BMW 2 F22-23': [
        'F22',  # Coupe (2014-2021)
        'F23'   # Convertible (2015-2021)
    ],
    'BMW 3 E90-93': [
        'E90',  # Sedan/Saloon (2005-2011)
        'E91',  # Estate/Touring (2005-2012)
        'E92',  # Coupe (2006-2013)
        'E93'   # Convertible (2007-2013)
    ],
    'BMW 3 F30-80': [
        'F30',  # Sedan/Saloon (2012-2019)
        'F31',  # Estate/Touring (2012-2019)
        'F34',  # Gran Turismo (2013-2020)
        'F80'   # M3 Sedan (2014-2018)
    ],
    'BMW 3 G20-21': [
        'G20',  # Sedan/Saloon (2019-present)
        'G21'   # Estate/Touring (2019-present)
    ],
    'BMW 4 F32-36': [
        'F32',  # Coupe (2013-2020)
        'F33',  # Convertible (2013-2020)
        'F36'   # Gran Coupe 4-door (2014-2020)
    ],
    'BMW 4 G22-26': [
        'G22',  # Coupe (2020-present)
        'G23',  # Convertible (2020-present)
        'G26'   # Gran Coupe 4-door (2021-present)
    ],
    'BMW 5 F10-18': [
        'F07',  # Gran Turismo fastback (2009-2017)
        'F10',  # Sedan/Saloon (2010-2017)
        'F11',  # Estate/Touring (2010-2017)
        'F18'   # Long-wheelbase sedan (2010-2017)
    ],
    'BMW 5 G30-38': [
        'G30',  # Sedan/Saloon (2017-present)
        'G31',  # Estate/Touring (2017-present)
        'G38'   # Long-wheelbase sedan (2017-present)
    ],
    'BMW 6 F06-13': [
        'F06',  # Gran Coupe 4-door (2012-2018)
        'F12',  # Convertible 2-door (2011-2018)
        'F13'   # Coupe 2-door (2011-2017)
    ],
    'BMW 7 F01-F04': [
        'F01',  # Standard wheelbase sedan (2008-2015)
        'F02',  # Long wheelbase sedan (2008-2015)
        'F03',  # High Security armored (2008-2015)
        'F04'   # ActiveHybrid model (2008-2015)
    ],
    'BMW 7 G11-12': [
        'G11',  # Standard wheelbase sedan (2015-2022)
        'G12'   # Long wheelbase sedan (2015-2022)
    ],
    'BMW 8 G14-16': [
        'G14',  # Coupe (2018-present)
        'G15',  # Convertible (2018-present)
        'G16'   # Gran Coupe 4-door (2019-present)
    ],
    'BMW M3 G80-81': [
        'G80',  # M3 Sedan (2020-present)
        'G81'   # M3 Touring (2022-present)
    ],
    'BMW M8 F91-93': [
        'F91',  # M8 Coupe (2019-present)
        'F92',  # M8 Convertible (2019-present)
        'F93'   # M8 Gran Coupe (2019-present)
    ],
    'BMW X1 F48-49': [
        'F48',  # First generation (2015-2022)
        'F49'   # China-specific long wheelbase (2016-2022)
    ],
    'Mercedes-Benz B-Class W242-246': [
        'W242',  # First generation (2005-2011)
        'W245',  # Second generation (2011-2019)
        'W246',  # Third generation (2019-present)
        'W247'   # Fourth generation (2022-present)
    ],
    'Mercedes-Benz Sprinter 907-910': [
        '907',  # First generation (1995-2006)
        '908',  # Second generation (2006-2018)
        '909',  # Third generation (2018-present)
        '910'   # Electric version (2023-present)
    ]
}