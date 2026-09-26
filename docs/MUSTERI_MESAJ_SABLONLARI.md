# Etsy Order Issue Message Templates

These templates are drafts only. Replace every `{placeholder}` before sending and confirm the final message manually. Nothing in this document authorizes an Etsy message to be sent.

## 1. Name is too long or contains an unsupported character

```text
Hi {buyer_first_name},

Thank you for your order! The name "{submitted_name}" is either longer than 11 letters or includes a character our name font does not support. We suggest printing it as "{suggested_name}".

Could you please confirm this spelling, or send us another version with up to 11 letters?

Lena & Serdar
AstroLoveArt
```

## 2. Message is longer than 35 characters

```text
Hi {buyer_first_name},

Thank you for your order! Your message is longer than the 35-character limit. We suggest shortening it to:

"{suggested_message}"

Please confirm this version, or send us another message with up to 35 characters.

Lena & Serdar
AstroLoveArt
```

## 3. Personalization field is blank

```text
Hi {buyer_first_name},

Thank you for your order! We still need the personalization details for your {sign_a} and {sign_b} print. Please send us:

Name for {sign_a}: {name_a}
Name for {sign_b}: {name_b}
Message, up to 35 characters: {message}

Once we receive these details, we can continue preparing your order.

Lena & Serdar
AstroLoveArt
```

## 4. Left and right names for the same zodiac sign

```text
Hi {buyer_first_name},

Thank you for your order! Since both sides feature {zodiac_sign}, we would like to confirm the name placement before we prepare your print:

Left: {left_name}
Right: {right_name}

Please reply "OK" if this is correct, or tell us which names to switch.

Lena & Serdar
AstroLoveArt
```

## 5. Short delay before printing for file review

```text
Hi {buyer_first_name},

We wanted to let you know that we are doing an extra file check before your order goes to print. This will cause a short delay, and the new estimated date is {date}.

Thank you for your patience. We will keep you updated if anything changes.

Lena & Serdar
AstroLoveArt
```

## 6. Shipping tracking number

```text
Hi {buyer_first_name},

Good news, your order has shipped! Your tracking number is {tracking_number} with {carrier}.

You can follow it here: {tracking_url}

Please allow a little time for the first tracking update to appear.

Lena & Serdar
AstroLoveArt
```

## order_router correspondence

| Template | `order_router` state or no-send reason | Related validation reason |
|---|---|---|
| 1 | `ISIM_BEKLIYOR`: personalization answer exists, so the order is not sent to Prodigi | `UZUN_ISIM`, `EMOJI`, `KARAKTER`, `KIRIL_ISIM`, or `ALFABE_ISIM` |
| 2 | `ISIM_BEKLIYOR`: personalization answer exists, so the order is not sent to Prodigi | `UZUN_MESAJ` |
| 3 | `ISIM_BEKLIYOR`: personalization answer exists, so the order is not sent to Prodigi | `BOS` or `EKSIK_SORU` |
| 4 | `ISIM_BEKLIYOR`: personalization answer exists, so the order is not sent to Prodigi | Same-sign pairs use the `LEFT` and `RIGHT` fields; confirmation is the spelling and placement check |
| 5 | No dedicated automatic reason exists; use only after a manual file-review delay decision while the order has not been sent | Manual file check |
| 6 | Not a Prodigi no-send reason; use after the router records the order as `shipped` and tracking details are available | Shipment tracking available |
