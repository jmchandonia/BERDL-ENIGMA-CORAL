package gov.lbl.enigma.app;

import java.io.File;
import java.util.Arrays;

import com.fasterxml.jackson.databind.ObjectMapper;

import us.kbase.genericsutil.GenericsUtilCommon;
import us.kbase.kbasegenerics.DimensionContext;
import us.kbase.kbasegenerics.HNDArray;
import us.kbase.kbasegenerics.NDArray;
import us.kbase.kbasegenerics.TypedValue;
import us.kbase.kbasegenerics.TypedValues;

import static us.kbase.genericsutil.GenericsUtilCommon.PRINT_BRIEF;
import static us.kbase.genericsutil.GenericsUtilCommon.PRINT_OREF;
import static us.kbase.genericsutil.GenericsUtilCommon.getRefLinks;
import static us.kbase.genericsutil.GenericsUtilCommon.validate;

/** Check a CORAL generic ndarray against the production ontology authority. */
public class CheckGenericProduction {
    public static void main(String[] argv) {
        try {
            new GenericsUtilCommon(Arrays.asList(
                "/home/coral/prod/data_import/ontologies/enigma_specific_ontology.obo",
                "/home/coral/prod/data_import/ontologies/data_type_ontology.obo",
                "/home/coral/prod/data_import/ontologies/chebi.obo",
                "/home/coral/prod/data_import/ontologies/context_measurement_ontology.obo",
                "/home/coral/prod/data_import/ontologies/unit_standalone.obo",
                "/home/coral/prod/data_import/ontologies/aro.obo",
                "/home/coral/prod/data_import/ontologies/mibig.obo"
            ));

            ObjectMapper mapper = new ObjectMapper();
            File file = new File(argv[0]);
            HNDArray hnda;
            try {
                hnda = mapper.readValue(file, HNDArray.class);
            } catch (Exception heterogeneousError) {
                NDArray nda = mapper.readValue(file, NDArray.class);
                hnda = GenericsUtilCommon.makeHNDArray(nda);
            }

            if (hnda.getArrayContext() != null) {
                for (TypedValue value : hnda.getArrayContext()) {
                    System.out.println("property: " + GenericsUtilCommon.toString(value, PRINT_OREF));
                    validate(value);
                }
            }
            int expectedSize = 1;
            for (DimensionContext dimension : hnda.getDimContext()) {
                System.out.println("dim: " + GenericsUtilCommon.toString(dimension.getDataType(), PRINT_OREF));
                for (TypedValues values : dimension.getTypedValues()) {
                    String rendered = GenericsUtilCommon.toString(values, PRINT_OREF);
                    System.out.println("dim_var: " + rendered);
                    if (rendered.indexOf("; ") > -1) {
                        System.out.println("composite_microtype: " + GenericsUtilCommon.toString(values, PRINT_BRIEF));
                    }
                }
                validate(dimension);
                int size = (int) dimension.getSize().longValue();
                expectedSize *= size;
                System.out.println("dim_size: " + size);
            }
            for (TypedValues values : hnda.getTypedValues()) {
                String rendered = GenericsUtilCommon.toString(values, PRINT_OREF);
                System.out.println("data_var: " + rendered);
                if (rendered.indexOf("; ") > -1) {
                    System.out.println("composite_microtype: " + GenericsUtilCommon.toString(values, PRINT_BRIEF));
                }
                validate(values, expectedSize);
            }
            if (getRefLinks(hnda) == null) {
                throw new Exception("Generic has no references; data islands not allowed.");
            }
            System.out.println("Generic is OK!");
        } catch (Exception error) {
            System.out.println("Exception: " + error.getMessage());
            error.printStackTrace();
            System.exit(1);
        }
    }
}
