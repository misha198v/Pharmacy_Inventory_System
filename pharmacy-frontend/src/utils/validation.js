export const validators = {
  required: (value) => value?.trim() ? null : 'This field is required',
  minLength: (min) => (value) => value?.length >= min ? null : `Minimum ${min} characters`,
  maxLength: (max) => (value) => value?.length <= max ? null : `Maximum ${max} characters`,
  email: (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) ? null : 'Invalid email',
  number: (value) => !isNaN(value) ? null : 'Must be a number',
  positive: (value) => Number(value) > 0 ? null : 'Must be positive',
  futureDate: (value) => new Date(value) > new Date() ? null : 'Date must be in the future',
};

export function validate(formData, schema) {
  const errors = {};
  Object.entries(schema).forEach(([field, validators_array]) => {
    const value = formData[field];
    for (let validator of validators_array) {
      const error = validator(value);
      if (error) {
        errors[field] = error;
        break;
      }
    }
  });
  return errors;
}