// Форматирование адреса с полными названиями
export const formatAddress = (locality: string, street: string, number: string): string => {
  // Расширяем сокращения в названиях улиц
  const expandedStreet = street
    .replace(/\bул\.\s*/gi, 'улица ')
    .replace(/\bпер\.\s*/gi, 'переулок ')
    .replace(/\bпр-т\s*/gi, 'проспект ')
    .replace(/\bпр\.\s*/gi, 'проспект ')
    .replace(/\bпл\.\s*/gi, 'площадь ')
    .replace(/\bб-р\s*/gi, 'бульвар ')
    .replace(/\bш\.\s*/gi, 'шоссе ')
    .replace(/\bнаб\.\s*/gi, 'набережная ')
    .replace(/\bпроезд\.\s*/gi, 'проезд ')
    .replace(/\bтупик\.\s*/gi, 'тупик ')
    .trim();

  // Форматируем номер дома (может содержать корпус и строение)
  // Например: "50 к1 с15" или "50к1с15" или "50 корп 1 стр 15"
  const formattedNumber = number
    .replace(/\bкорп\.?\s*/gi, 'к')
    .replace(/\bкорпус\s*/gi, 'к')
    .replace(/\bстр\.?\s*/gi, 'с')
    .replace(/\bстроение\s*/gi, 'с')
    .replace(/\bлит\.?\s*/gi, 'л')
    .replace(/\bлитера\s*/gi, 'л')
    .trim();

  return `${locality}, ${expandedStreet}, ${formattedNumber}`;
};

// Нормализованный формат для отображения
export const formatNormalizedAddress = (locality: string, street: string, number: string): string => {
  return `Нормализованный адрес: ${formatAddress(locality, street, number)}`;
};
