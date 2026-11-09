export function mapsUrl(address: string, pincode: string): string {
  const place = address ? `${address}, ${pincode}` : pincode;
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(place)}`;
}
