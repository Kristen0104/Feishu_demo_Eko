function stableValue(value) {
  if (Array.isArray(value)) {
    return value.map(stableValue)
  }
  if (value && typeof value === 'object') {
    return Object.keys(value)
      .sort()
      .reduce((result, key) => {
        result[key] = stableValue(value[key])
        return result
      }, {})
  }
  return value
}

export function hasSnapshotChanged(currentSnapshot, nextSnapshot) {
  const current = stableValue(currentSnapshot || {})
  const next = stableValue(nextSnapshot || {})
  return JSON.stringify(current) !== JSON.stringify(next)
}
