// Lokasi: frontend/babel.config.js

module.exports = function (api) {
  api.cache(true);
  return {
    presets: ["babel-preset-expo"],
    plugins: [
      // Only required plugin: keep Reanimated last
      "react-native-reanimated/plugin",
    ],
  };
};