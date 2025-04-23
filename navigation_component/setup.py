import setuptools

setuptools.setup(
    name="streamlit-navigation-component",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A custom navigation component for Streamlit",
    long_description="A custom navigation menu with hierarchical structure for Streamlit applications",
    long_description_content_type="text/plain",
    url="",
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=[],
    python_requires=">=3.6",
    install_requires=[
        "streamlit >= 0.63",
    ],
)