module.exports = function(api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    plugins: [
      [
        'module-resolver',
        {
          root: ['./'],
          alias: {
            '@': './src',
            '@features': './src/features',
            '@components': './src/components',
            '@services': './src/services',
            '@types': './src/types',
            '@utils': './src/utils',
            '@config': './src/config',
          },
        },
      ],
    ],
  };
};
