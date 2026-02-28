export const PROFILE_LIMITS = {
  first_name: 250,
  last_name: 250,
  address_line1: 100,
  address_line2: 100,
  address_line3: 100,
  zip_code: 6,
  phone_number: 12,
  region: 100
} as const;

export type ProfileForm = {
  first_name: string;
  last_name: string;
  address_line1: string;
  address_line2: string;
  address_line3: string;
  zip_code: string;
  phone_number: string;
  region: string;
};

export type ProfileFieldErrors = Partial<Record<keyof ProfileForm, string>>;

export function validateProfileForm(values: ProfileForm): string[] {
  const errors: string[] = [];

  for (const [key, maxLen] of Object.entries(PROFILE_LIMITS)) {
    const value = values[key as keyof ProfileForm];
    if (value.length > maxLen) {
      errors.push(`${labelFor(key)} must be at most ${maxLen} characters.`);
    }
  }

  if (values.zip_code && !/^[a-zA-Z0-9-]+$/.test(values.zip_code)) {
    errors.push("Zip Code can contain letters, numbers, and '-'.");
  }
  if (values.phone_number && !/^[0-9+() -]+$/.test(values.phone_number)) {
    errors.push("Phone Number contains invalid characters.");
  }

  return errors;
}

export function validateProfileFieldErrors(values: ProfileForm): ProfileFieldErrors {
  const errors: ProfileFieldErrors = {};

  for (const [key, maxLen] of Object.entries(PROFILE_LIMITS)) {
    const typedKey = key as keyof ProfileForm;
    const value = values[typedKey];
    if (value.length > maxLen) {
      errors[typedKey] = `${labelFor(key)} must be at most ${maxLen} characters.`;
    }
  }

  if (values.zip_code && !/^[a-zA-Z0-9-]+$/.test(values.zip_code)) {
    errors.zip_code = "Zip Code can contain letters, numbers, and '-'.";
  }
  if (values.phone_number && !/^[0-9+() -]+$/.test(values.phone_number)) {
    errors.phone_number = "Phone Number contains invalid characters.";
  }

  return errors;
}

function labelFor(key: string): string {
  return key
    .split("_")
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
}
